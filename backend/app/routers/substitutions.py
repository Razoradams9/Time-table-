"""Substitution viewing, manual override, and AI suggestions (Req 5, 6, 7.2)."""
from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import (
    Role,
    Substitution,
    SubstitutionSource,
    SubstitutionStatus,
    Teacher,
)
from app.schemas import (
    Candidate,
    ManualAssignRequest,
    SubstitutionDetail,
    Suggestion,
)
from app.security import get_current_teacher, require_hod
from app.services import audit
from app.services.ai_assist import explain_substitution, suggest_for_uncovered
from app.services.notifications import notify
from app.services.substitution_engine import rank_candidates

router = APIRouter(prefix="/api/substitutions", tags=["substitutions"])


def to_detail(sub: Substitution) -> SubstitutionDetail:
    entry = sub.timetable_entry
    return SubstitutionDetail(
        id=sub.id,
        override_date=sub.override_date,
        status=sub.status,
        source=sub.source,
        explanation=sub.explanation,
        period=f"P{entry.time_slot.period_index + 1} ({entry.time_slot.start_time}-{entry.time_slot.end_time})",
        day_of_week=entry.time_slot.day_of_week,
        subject=entry.subject.name,
        class_section=entry.class_section.name,
        room=entry.room.name,
        absent_teacher=sub.absent_teacher.name,
        substitute_teacher=sub.substitute_teacher.name if sub.substitute_teacher else None,
    )


@router.get("", response_model=list[SubstitutionDetail])
def list_substitutions(
    on: date | None = None,
    db: Session = Depends(get_db),
    current: Teacher = Depends(get_current_teacher),
):
    stmt = select(Substitution).where(Substitution.status != SubstitutionStatus.CANCELLED)
    if on:
        stmt = stmt.where(Substitution.override_date == on)
    if current.role != Role.HOD:
        # Teachers see subs where they are the substitute or the absent teacher.
        stmt = stmt.where(
            (Substitution.substitute_teacher_id == current.id)
            | (Substitution.absent_teacher_id == current.id)
        )
    subs = db.scalars(stmt.order_by(Substitution.override_date.desc())).all()
    return [to_detail(s) for s in subs]


@router.get("/{sub_id}/candidates", response_model=list[Candidate])
def candidates(sub_id: int, db: Session = Depends(get_db), hod: Teacher = Depends(require_hod)):
    sub = db.get(Substitution, sub_id)
    if sub is None:
        raise HTTPException(status_code=404, detail="Substitution not found.")
    ranked = rank_candidates(db, sub.timetable_entry, sub.override_date)
    return [
        Candidate(teacher_id=c.teacher.id, name=c.teacher.name, score=round(c.score, 1), reason=c.reason)
        for c in ranked
    ]


@router.get("/{sub_id}/suggestions", response_model=list[Suggestion])
def suggestions(sub_id: int, db: Session = Depends(get_db), hod: Teacher = Depends(require_hod)):
    sub = db.get(Substitution, sub_id)
    if sub is None:
        raise HTTPException(status_code=404, detail="Substitution not found.")
    return suggest_for_uncovered(db, sub)


@router.get("/{sub_id}/explanation")
def explanation(sub_id: int, db: Session = Depends(get_db), current: Teacher = Depends(get_current_teacher)):
    sub = db.get(Substitution, sub_id)
    if sub is None:
        raise HTTPException(status_code=404, detail="Substitution not found.")
    return {"explanation": explain_substitution(sub)}


@router.post("/{sub_id}/assign", response_model=SubstitutionDetail)
def manual_assign(
    sub_id: int,
    payload: ManualAssignRequest,
    db: Session = Depends(get_db),
    hod: Teacher = Depends(require_hod),
):
    """HOD manually overrides/reassigns a substitute (Req 7.2)."""
    sub = db.get(Substitution, sub_id)
    if sub is None:
        raise HTTPException(status_code=404, detail="Substitution not found.")
    new_teacher = db.get(Teacher, payload.substitute_teacher_id)
    if new_teacher is None:
        raise HTTPException(status_code=404, detail="Teacher not found.")

    # Validate the chosen teacher is genuinely free this slot (avoid clashes).
    ranked = rank_candidates(db, sub.timetable_entry, sub.override_date)
    eligible_ids = {c.teacher.id for c in ranked}
    if new_teacher.id not in eligible_ids and new_teacher.id != sub.substitute_teacher_id:
        raise HTTPException(
            status_code=409,
            detail=f"{new_teacher.name} is not free for this period (teaching, on leave, or over limit).",
        )

    old = sub.substitute_teacher
    sub.substitute_teacher_id = new_teacher.id
    sub.status = SubstitutionStatus.ASSIGNED
    sub.source = SubstitutionSource.MANUAL
    sub.explanation = f"Manually assigned by {hod.name}."

    entry = sub.timetable_entry
    period = entry.time_slot.period_index + 1
    if old and old.id != new_teacher.id:
        notify(db, old, "Substitution reassigned",
               f"You no longer cover {entry.subject.name} ({entry.class_section.name}) on {sub.override_date}.")
    notify(db, new_teacher, "New substitution assigned",
           f"You are covering {entry.subject.name} for {entry.class_section.name} "
           f"on {sub.override_date} (period {period}, room {entry.room.name}).")

    audit.log(db, actor_id=hod.id, action="OVERRIDE", entity="substitution", entity_id=sub.id,
              detail=f"Assigned {new_teacher.name}.")
    db.commit()
    db.refresh(sub)
    return to_detail(sub)
