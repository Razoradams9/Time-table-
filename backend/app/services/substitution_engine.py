"""Rule-based automated substitution engine (Requirement 5).

Design principle (Req 6.3): final assignment logic is fully rule-based and
auditable. The AI layer only adds suggestions/explanations on top.

For each affected period we:
  1. Find teachers who are FREE in that slot on that date (not teaching, not on
     leave, not already substituting elsewhere that slot).
  2. Rank them by: subject/department match, workload that day/week, fairness
     (subs already given this week), respecting the daily period cap.
  3. Assign the top candidate, recording a plain-language explanation.
  4. If nobody is eligible, mark the period UNCOVERED.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.models import (
    Availability,
    Leave,
    LeavePeriod,
    LeaveScope,
    LeaveStatus,
    Substitution,
    SubstitutionSource,
    SubstitutionStatus,
    Teacher,
    TimeSlot,
    TimetableEntry,
)


def _week_bounds(d: date) -> tuple[date, date]:
    start = d - timedelta(days=d.weekday())  # Monday
    return start, start + timedelta(days=6)


@dataclass
class RankedCandidate:
    teacher: Teacher
    score: float
    reason: str


def _active_entries_on(db: Session, d: date) -> list[TimetableEntry]:
    """Base entries whose weekday matches the date, from the active timetable."""
    dow = d.weekday()
    return db.scalars(
        select(TimetableEntry)
        .join(TimeSlot, TimetableEntry.time_slot_id == TimeSlot.id)
        .where(TimetableEntry.is_active.is_(True), TimeSlot.day_of_week == dow)
    ).all()


def _teachers_on_leave(db: Session, d: date) -> dict[int, set[int]]:
    """teacher_id -> set of slot ids they are absent for on date d.

    Full-day leave maps to every active slot for that day's weekday.
    """
    dow = d.weekday()
    day_slot_ids = {s.id for s in db.scalars(select(TimeSlot).where(TimeSlot.day_of_week == dow)).all()}
    result: dict[int, set[int]] = {}
    leaves = db.scalars(
        select(Leave).where(Leave.leave_date == d, Leave.status == LeaveStatus.ACTIVE)
    ).all()
    for lv in leaves:
        if lv.scope == LeaveScope.FULL_DAY:
            result.setdefault(lv.teacher_id, set()).update(day_slot_ids)
        else:
            for p in lv.periods:
                result.setdefault(lv.teacher_id, set()).add(p.time_slot_id)
    return result


def _availability_map(db: Session) -> dict[int, set[int] | None]:
    """teacher_id -> declared available slot ids, or None if none declared (=any)."""
    rows = db.scalars(select(Availability)).all()
    declared: dict[int, set[int]] = {}
    for r in rows:
        declared.setdefault(r.teacher_id, set()).add(r.time_slot_id)
    result: dict[int, set[int] | None] = {}
    for t in db.scalars(select(Teacher)).all():
        result[t.id] = declared.get(t.id)  # None means unrestricted
    return result


def _busy_slots_from_base(db: Session, d: date) -> dict[int, set[int]]:
    """teacher_id -> slot ids they teach in the base timetable on this weekday."""
    result: dict[int, set[int]] = {}
    for e in _active_entries_on(db, d):
        result.setdefault(e.teacher_id, set()).add(e.time_slot_id)
    return result


def _busy_slots_from_subs(db: Session, d: date) -> dict[int, set[int]]:
    """teacher_id -> slot ids where they are already substituting on date d."""
    result: dict[int, set[int]] = {}
    subs = db.scalars(
        select(Substitution).where(
            Substitution.override_date == d,
            Substitution.status == SubstitutionStatus.ASSIGNED,
            Substitution.substitute_teacher_id.is_not(None),
        )
    ).all()
    for s in subs:
        entry = s.timetable_entry
        result.setdefault(s.substitute_teacher_id, set()).add(entry.time_slot_id)
    return result


def _subs_this_week(db: Session, d: date) -> dict[int, int]:
    """teacher_id -> count of substitutions already given this week."""
    start, end = _week_bounds(d)
    subs = db.scalars(
        select(Substitution).where(
            Substitution.override_date >= start,
            Substitution.override_date <= end,
            Substitution.status == SubstitutionStatus.ASSIGNED,
            Substitution.substitute_teacher_id.is_not(None),
        )
    ).all()
    counts: dict[int, int] = {}
    for s in subs:
        counts[s.substitute_teacher_id] = counts.get(s.substitute_teacher_id, 0) + 1
    return counts


def _period_index_of_slot(db: Session, slot_id: int) -> int:
    slot = db.get(TimeSlot, slot_id)
    return slot.period_index if slot else -1


def _fatigue_assessment(
    occupied_periods: set[int], target_period: int
) -> tuple[float, list[str]]:
    """Score how much this assignment respects the teacher's rest.

    Higher score = better rested outcome. Looks at the periods the teacher
    already works that day and the period we'd add, then rewards keeping gaps
    and penalizes back-to-back teaching and long unbroken runs.
    """
    from app.config import settings

    score = 0.0
    notes: list[str] = []
    if not occupied_periods:
        # Their only period that day: maximally rested. Small reward.
        score += settings.fatigue_gap_bonus
        notes.append("only period that day")
        return score, notes

    # Adjacency: is the new period immediately before/after an existing one?
    touches_before = (target_period - 1) in occupied_periods
    touches_after = (target_period + 1) in occupied_periods
    if touches_before and touches_after:
        # Fills a gap -> sandwiched, worst for rest.
        score -= settings.fatigue_adjacency_penalty * 2
        notes.append("would remove a rest gap (back-to-back both sides)")
    elif touches_before or touches_after:
        score -= settings.fatigue_adjacency_penalty
        notes.append("adjacent to an existing period")
    else:
        # Isolated with a buffer on both sides -> keeps rest.
        score += settings.fatigue_gap_bonus
        notes.append("keeps a free-period buffer")

    # Consecutive run length that this assignment would create.
    run = 1
    p = target_period - 1
    while p in occupied_periods:
        run += 1
        p -= 1
    p = target_period + 1
    while p in occupied_periods:
        run += 1
        p += 1
    if run > settings.fatigue_max_consecutive:
        over = run - settings.fatigue_max_consecutive
        score -= settings.fatigue_run_penalty * over
        notes.append(f"{run} periods in a row")

    return score, notes


def rank_candidates(
    db: Session,
    entry: TimetableEntry,
    d: date,
    *,
    exclude_teacher_ids: set[int] | None = None,
) -> list[RankedCandidate]:
    """Rank eligible free teachers for covering `entry` on date `d`."""
    exclude = exclude_teacher_ids or set()
    slot_id = entry.time_slot_id
    subject = entry.subject
    dept_id = subject.department_id
    target_period = _period_index_of_slot(db, slot_id)

    on_leave = _teachers_on_leave(db, d)
    base_busy = _busy_slots_from_base(db, d)
    sub_busy = _busy_slots_from_subs(db, d)
    avail = _availability_map(db)
    week_counts = _subs_this_week(db, d)

    # Map slot ids -> period_index so we can reason about adjacency/gaps.
    slot_period = {
        s.id: s.period_index for s in db.scalars(select(TimeSlot)).all()
    }

    # Periods each teacher already has that day (base + subs) for workload + cap.
    day_load: dict[int, int] = {}
    occupied_periods: dict[int, set[int]] = {}
    for tid, slots in base_busy.items():
        day_load[tid] = day_load.get(tid, 0) + len(slots)
        occupied_periods.setdefault(tid, set()).update(
            slot_period.get(s, -1) for s in slots
        )
    for tid, slots in sub_busy.items():
        day_load[tid] = day_load.get(tid, 0) + len(slots)
        occupied_periods.setdefault(tid, set()).update(
            slot_period.get(s, -1) for s in slots
        )

    ranked: list[RankedCandidate] = []
    for teacher in db.scalars(select(Teacher).where(Teacher.is_active.is_(True))).all():
        tid = teacher.id
        if tid == entry.teacher_id or tid in exclude:
            continue
        # Not teaching a role-only account? HOD can still cover if qualified/free.
        # Must be free this slot: not on leave, not teaching, not already subbing.
        if slot_id in on_leave.get(tid, set()):
            continue
        if slot_id in base_busy.get(tid, set()):
            continue
        if slot_id in sub_busy.get(tid, set()):
            continue
        declared = avail.get(tid)
        if declared is not None and slot_id not in declared:
            continue  # explicitly unavailable this slot
        # Daily cap (Req 5.4).
        if day_load.get(tid, 0) >= teacher.max_periods_per_day:
            continue

        # ----- Scoring (higher is better) -----
        score = 0.0
        reasons: list[str] = ["Free this period"]

        can_teach_subject = any(s.id == subject.id for s in teacher.subjects)
        if can_teach_subject:
            score += 50
            reasons.append("teaches this subject")
        elif teacher.department_id and teacher.department_id == dept_id:
            score += 30
            reasons.append("same department")

        given = week_counts.get(tid, 0)
        # Fairness: fewer substitutions this week -> higher score.
        score += max(0, (settings.max_substitutions_per_week - given)) * 8
        reasons.append(f"{given} substitution(s) this week")

        # ----- Fatigue / rest: prefer teachers who stay well-rested -----
        load = day_load.get(tid, 0)
        # Lighter day so far -> higher score (rest-aware weight).
        score -= load * settings.fatigue_daily_load_penalty
        reasons.append(f"{load} period(s) today")

        fatigue_score, fatigue_notes = _fatigue_assessment(
            occupied_periods.get(tid, set()), target_period
        )
        score += fatigue_score
        reasons.extend(fatigue_notes)

        # Respect the weekly cap as a soft preference (hard cap could be enabled).
        if given >= settings.max_substitutions_per_week:
            score -= 40
            reasons.append("at weekly substitution cap")

        ranked.append(
            RankedCandidate(teacher=teacher, score=score, reason=", ".join(reasons))
        )

    ranked.sort(key=lambda c: c.score, reverse=True)
    return ranked


def assign_substitutes_for_leave(db: Session, leave: Leave) -> list[Substitution]:
    """Create substitution overrides for every affected period of a leave."""
    d = leave.leave_date
    dow = d.weekday()

    # Which base entries of the absent teacher are affected?
    entries = db.scalars(
        select(TimetableEntry)
        .join(TimeSlot, TimetableEntry.time_slot_id == TimeSlot.id)
        .where(
            TimetableEntry.is_active.is_(True),
            TimetableEntry.teacher_id == leave.teacher_id,
            TimeSlot.day_of_week == dow,
        )
    ).all()

    if leave.scope == LeaveScope.PERIODS:
        affected_slot_ids = {p.time_slot_id for p in leave.periods}
        entries = [e for e in entries if e.time_slot_id in affected_slot_ids]

    created: list[Substitution] = []
    # Track teachers we assign in this run to avoid overlap across periods (Req 5.8).
    assigned_slot_teacher: dict[int, set[int]] = {}  # slot_id -> teacher_ids used

    for entry in entries:
        # Skip if a substitution already exists for this entry+date.
        existing = db.scalar(
            select(Substitution).where(
                Substitution.override_date == d,
                Substitution.timetable_entry_id == entry.id,
                Substitution.status != SubstitutionStatus.CANCELLED,
            )
        )
        if existing:
            continue

        used_this_slot = assigned_slot_teacher.get(entry.time_slot_id, set())
        candidates = rank_candidates(db, entry, d, exclude_teacher_ids=used_this_slot)

        sub = Substitution(
            override_date=d,
            timetable_entry_id=entry.id,
            leave_id=leave.id,
            absent_teacher_id=leave.teacher_id,
        )
        if candidates:
            top = candidates[0]
            sub.substitute_teacher_id = top.teacher.id
            sub.status = SubstitutionStatus.ASSIGNED
            sub.source = SubstitutionSource.AUTO
            sub.explanation = top.reason
            assigned_slot_teacher.setdefault(entry.time_slot_id, set()).add(top.teacher.id)
        else:
            sub.status = SubstitutionStatus.UNCOVERED
            sub.source = SubstitutionSource.AUTO
            sub.explanation = "No eligible teacher was free for this period."
        db.add(sub)
        db.flush()  # get id
        created.append(sub)

    return created
