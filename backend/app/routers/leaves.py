"""Leave registration portal (Requirement 4) + triggers substitution engine."""
from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import (
    Leave,
    LeavePeriod,
    LeaveScope,
    LeaveStatus,
    Role,
    Substitution,
    SubstitutionStatus,
    Teacher,
    TimeSlot,
)
from app.schemas import LeaveCreate, LeaveOut
from app.security import get_current_teacher
from app.services import audit
from app.services.notifications import notify
from app.services.substitution_engine import assign_substitutes_for_leave

router = APIRouter(prefix="/api/leaves", tags=["leaves"])


def _hods(db: Session) -> list[Teacher]:
    return db.scalars(select(Teacher).where(Teacher.role == Role.HOD)).all()


def _notify_substitutes(db: Session, subs: list[Substitution]) -> None:
    for s in subs:
        entry = s.timetable_entry
        period = entry.time_slot.period_index + 1
        if s.status == SubstitutionStatus.ASSIGNED and s.substitute_teacher:
            notify(
                db,
                s.substitute_teacher,
                "New substitution assigned",
                f"You are covering {entry.subject.name} for {entry.class_section.name} "
                f"on {s.override_date} (period {period}, room {entry.room.name}).",
            )
        elif s.status == SubstitutionStatus.UNCOVERED:
            for hod in _hods(db):
                notify(
                    db,
                    hod,
                    "Uncovered period needs attention",
                    f"{entry.subject.name} for {entry.class_section.name} on {s.override_date} "
                    f"(period {period}) could not be covered automatically.",
                )


@router.post("", response_model=LeaveOut)
def create_leave(
    payload: LeaveCreate,
    db: Session = Depends(get_db),
    current: Teacher = Depends(get_current_teacher),
):
    # No past dates (Req 4.3).
    if payload.leave_date < date.today():
        raise HTTPException(status_code=400, detail="Cannot register leave for a past date.")

    # Prevent overlapping/duplicate leave (Req 4.2).
    existing = db.scalar(
        select(Leave).where(
            Leave.teacher_id == current.id,
            Leave.leave_date == payload.leave_date,
            Leave.status == LeaveStatus.ACTIVE,
        )
    )
    if existing:
        raise HTTPException(status_code=409, detail="You already have an active leave on this date.")

    if payload.scope == LeaveScope.PERIODS and not payload.time_slot_ids:
        raise HTTPException(status_code=400, detail="Select at least one period for a partial-day leave.")

    leave = Leave(
        teacher_id=current.id,
        leave_date=payload.leave_date,
        scope=payload.scope,
        reason=payload.reason,
        status=LeaveStatus.ACTIVE,
    )
    db.add(leave)
    db.flush()

    if payload.scope == LeaveScope.PERIODS:
        valid_slot_ids = {s.id for s in db.scalars(select(TimeSlot)).all()}
        for sid in payload.time_slot_ids:
            if sid not in valid_slot_ids:
                raise HTTPException(status_code=400, detail=f"Unknown time slot {sid}.")
            db.add(LeavePeriod(leave_id=leave.id, time_slot_id=sid))
        db.flush()

    # Identify affected periods and assign substitutes (Req 4.4 + Req 5).
    subs = assign_substitutes_for_leave(db, leave)

    audit.log(db, actor_id=current.id, action="CREATE", entity="leave", entity_id=leave.id,
              detail=f"{payload.scope.value} on {payload.leave_date}; {len(subs)} periods affected.")

    # Notify HOD of the leave (Req 8.2), and substitutes/HOD of assignments.
    for hod in _hods(db):
        notify(db, hod, "Leave registered",
               f"{current.name} registered leave on {payload.leave_date} "
               f"({payload.scope.value}). {len(subs)} period(s) affected.")
    _notify_substitutes(db, subs)

    db.commit()
    db.refresh(leave)
    return leave


@router.get("", response_model=list[LeaveOut])
def my_leaves(db: Session = Depends(get_db), current: Teacher = Depends(get_current_teacher)):
    stmt = select(Leave).order_by(Leave.leave_date.desc())
    if current.role != Role.HOD:
        stmt = stmt.where(Leave.teacher_id == current.id)
    return db.scalars(stmt).all()


@router.delete("/{leave_id}", response_model=LeaveOut)
def cancel_leave(
    leave_id: int,
    db: Session = Depends(get_db),
    current: Teacher = Depends(get_current_teacher),
):
    leave = db.get(Leave, leave_id)
    if leave is None:
        raise HTTPException(status_code=404, detail="Leave not found.")
    if leave.teacher_id != current.id and current.role != Role.HOD:
        raise HTTPException(status_code=403, detail="You can only cancel your own leave.")
    if leave.status == LeaveStatus.CANCELLED:
        raise HTTPException(status_code=400, detail="Leave is already cancelled.")
    # Only before the leave date (Req 4.5).
    if leave.leave_date < date.today():
        raise HTTPException(status_code=400, detail="Cannot cancel a leave whose date has passed.")

    # Revert related substitutions and notify affected substitutes (Req 4.6).
    related = db.scalars(
        select(Substitution).where(
            Substitution.leave_id == leave.id,
            Substitution.status != SubstitutionStatus.CANCELLED,
        )
    ).all()
    for s in related:
        if s.status == SubstitutionStatus.ASSIGNED and s.substitute_teacher:
            entry = s.timetable_entry
            notify(
                db,
                s.substitute_teacher,
                "Substitution cancelled",
                f"The substitution for {entry.subject.name} ({entry.class_section.name}) "
                f"on {s.override_date} is no longer needed.",
            )
        s.status = SubstitutionStatus.CANCELLED

    leave.status = LeaveStatus.CANCELLED
    audit.log(db, actor_id=current.id, action="CANCEL", entity="leave", entity_id=leave.id,
              detail=f"Reverted {len(related)} substitution(s).")
    db.commit()
    db.refresh(leave)
    return leave
