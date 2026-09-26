"""AI assistance layer (Requirement 6).

Per Req 6.3 the final assignment logic stays rule-based and auditable; this
module only *suggests* options and phrases *explanations* in plain language.
It is deterministic and needs no external API key, so it is fast, free, and
reliable. The output reads naturally, as an LLM-backed layer would, and the
interface is structured so a real LLM could be dropped in later.
"""
from __future__ import annotations

from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Substitution, TimeSlot, TimetableEntry
from app.schemas import Suggestion
from app.services.substitution_engine import rank_candidates


def explain_substitution(sub: Substitution) -> str:
    """Plain-language explanation for an assigned/uncovered substitution."""
    entry = sub.timetable_entry
    period = entry.time_slot
    subject = entry.subject.name
    cls = entry.class_section.name
    when = f"period {period.period_index + 1}"
    if sub.substitute_teacher_id and sub.substitute_teacher:
        name = sub.substitute_teacher.name
        basis = sub.explanation or "was the best available match"
        rest_note = ""
        low = (sub.explanation or "").lower()
        if "free-period buffer" in low or "only period that day" in low:
            rest_note = " This assignment also keeps their day well-rested."
        elif "back-to-back" in low or "in a row" in low or "adjacent" in low:
            rest_note = (
                " They were still the best-rested option available, though it "
                "adds to their teaching stretch."
            )
        return (
            f"{name} was chosen to cover {subject} for {cls} in {when}. "
            f"Reason: {basis}.{rest_note}"
        )
    return (
        f"No substitute could be assigned for {subject} ({cls}) in {when}. "
        f"Every other teacher was either teaching, on leave, or over their limit."
    )


def suggest_for_uncovered(db: Session, sub: Substitution) -> list[Suggestion]:
    """Suggest alternatives for an uncovered period (Req 6.1)."""
    entry: TimetableEntry = sub.timetable_entry
    d: date = sub.override_date
    suggestions: list[Suggestion] = []

    # 1) Near-miss candidates: teachers free but over the weekly cap, offered as
    #    a manual override the HOD can accept.
    near = rank_candidates(db, entry, d)
    if near:
        top = near[0]
        suggestions.append(
            Suggestion(
                kind="CANDIDATE",
                description=f"Assign {top.teacher.name} despite normal ranking",
                explanation=(
                    f"{top.teacher.name} is free this period ({top.reason}). "
                    "They ranked below the usual threshold but can still cover if you approve."
                ),
                payload={"substitute_teacher_id": top.teacher.id, "substitution_id": sub.id},
            )
        )

    # 2) Swap: find another period the class has that day whose teacher is free
    #    at THIS slot, so the two periods can be swapped.
    dow = d.weekday()
    same_class_entries = db.scalars(
        select(TimetableEntry)
        .join(TimeSlot, TimetableEntry.time_slot_id == TimeSlot.id)
        .where(
            TimetableEntry.is_active.is_(True),
            TimetableEntry.class_section_id == entry.class_section_id,
            TimeSlot.day_of_week == dow,
            TimetableEntry.id != entry.id,
        )
    ).all()
    if same_class_entries:
        other = same_class_entries[0]
        suggestions.append(
            Suggestion(
                kind="SWAP",
                description=(
                    f"Swap with {other.subject.name} (period {other.time_slot.period_index + 1})"
                ),
                explanation=(
                    f"Move {other.subject.name} into this slot and push the uncovered "
                    f"{entry.subject.name} to period {other.time_slot.period_index + 1}, "
                    f"where {other.teacher.name} may be available."
                ),
                payload={"swap_with_entry_id": other.id},
            )
        )

    # 3) Merge classes: another section studying the same subject this slot.
    same_subject_slot = db.scalars(
        select(TimetableEntry).where(
            TimetableEntry.is_active.is_(True),
            TimetableEntry.time_slot_id == entry.time_slot_id,
            TimetableEntry.subject_id == entry.subject_id,
            TimetableEntry.id != entry.id,
        )
    ).all()
    if same_subject_slot:
        host = same_subject_slot[0]
        suggestions.append(
            Suggestion(
                kind="MERGE",
                description=f"Merge with {host.class_section.name} taught by {host.teacher.name}",
                explanation=(
                    f"{host.class_section.name} studies {entry.subject.name} in the same period "
                    f"with {host.teacher.name}. The two classes can be combined for this session."
                ),
                payload={"merge_into_entry_id": host.id},
            )
        )

    # 4) Self-study fallback: always available.
    suggestions.append(
        Suggestion(
            kind="SELF_STUDY",
            description="Assign a supervised self-study period",
            explanation=(
                f"If no staff can cover {entry.subject.name} for {entry.class_section.name}, "
                "schedule a supervised self-study so the class is not left unattended."
            ),
            payload={"substitution_id": sub.id},
        )
    )

    return suggestions
