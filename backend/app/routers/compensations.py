"""Compensation (make-up class) endpoints.

Owner teacher or HOD may confirm / reschedule / complete / repropose; cancel and
backfill are HOD only. Teachers only see their own records in the list, summary and
calendar (asking for another teacher's records is a 403).
"""
from __future__ import annotations

from datetime import date, datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Compensation, CompensationStatus, Role, Teacher
from app.schemas import (
    BackfillResult,
    CompensationCalendarItem,
    CompensationOut,
    CompensationSlotRequest,
    CompensationSuggestionOut,
    CompensationSummary,
)
from app.security import get_current_teacher, require_hod
from app.services import audit
from app.services import compensation as svc

router = APIRouter(prefix="/api/compensations", tags=["compensations"])

ACTIVE = svc.ACTIVE_STATUSES


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _get(db: Session, comp_id: int, current: Teacher, hod_only: bool = False) -> Compensation:
    comp = db.get(Compensation, comp_id)
    if comp is None:
        raise HTTPException(status_code=404, detail="Compensation not found.")
    if hod_only:
        if current.role != Role.HOD:
            raise HTTPException(status_code=403, detail="Only the HOD can do this.")
    elif comp.teacher_id != current.id and current.role != Role.HOD:
        raise HTTPException(status_code=403, detail="This make-up belongs to another teacher.")
    return comp


def _sweep(db: Session) -> None:
    if svc.sweep_past(db):
        db.commit()


def _visible_query(current: Teacher, teacher_id: int | None):
    stmt = select(Compensation)
    if current.role != Role.HOD:
        if teacher_id is not None and teacher_id != current.id:
            raise HTTPException(status_code=403, detail="You can only view your own make-ups.")
        stmt = stmt.where(Compensation.teacher_id == current.id)
    elif teacher_id is not None:
        stmt = stmt.where(Compensation.teacher_id == teacher_id)
    return stmt


def _slot_label(comp: Compensation) -> str:
    out = svc.to_out(comp)
    return f"{out.proposed_date} {out.proposed_period}" + (f" in {out.room}" if out.room else "")


@router.get("", response_model=list[CompensationOut])
def list_compensations(
    teacher_id: int | None = None,
    status: str | None = None,
    on: date | None = None,
    db: Session = Depends(get_db),
    current: Teacher = Depends(get_current_teacher),
):
    _sweep(db)
    stmt = _visible_query(current, teacher_id)
    if status:
        try:
            wanted = [CompensationStatus(s.strip().upper()) for s in status.split(",") if s.strip()]
        except ValueError:
            raise HTTPException(status_code=400, detail="Unknown status filter.")
        stmt = stmt.where(Compensation.status.in_(wanted))
    if on:
        stmt = stmt.where((Compensation.proposed_date == on) | (Compensation.missed_date == on))
    comps = db.scalars(stmt.order_by(Compensation.missed_date, Compensation.id)).all()
    ordinals = svc.period_ordinals(db)
    return [svc.to_out(c, ordinals) for c in comps]


@router.get("/summary", response_model=CompensationSummary)
def summary(
    teacher_id: int | None = None,
    db: Session = Depends(get_db),
    current: Teacher = Depends(get_current_teacher),
):
    _sweep(db)
    comps = db.scalars(_visible_query(current, teacher_id)).all()
    count = lambda st: sum(1 for c in comps if c.status == st)  # noqa: E731
    owed = sum(c.periods for c in comps if c.status in ACTIVE)
    return CompensationSummary(
        owed=owed,
        proposed=count(CompensationStatus.PROPOSED),
        scheduled=count(CompensationStatus.SCHEDULED),
        completed=count(CompensationStatus.COMPLETED),
        cancelled=count(CompensationStatus.CANCELLED),
    )


@router.get("/calendar", response_model=list[CompensationCalendarItem])
def calendar(
    on: date,
    db: Session = Depends(get_db),
    current: Teacher = Depends(get_current_teacher),
):
    _sweep(db)
    stmt = select(Compensation).where(
        Compensation.proposed_date == on,
        Compensation.status.in_(
            (CompensationStatus.PROPOSED, CompensationStatus.SCHEDULED, CompensationStatus.COMPLETED)
        ),
    )
    if current.role != Role.HOD:
        stmt = stmt.where(Compensation.teacher_id == current.id)
    comps = db.scalars(stmt.order_by(Compensation.id)).all()
    items = []
    for c in comps:
        slots = [c.proposed_time_slot] + ([c.proposed_time_slot2] if c.proposed_time_slot2 else [])
        items.append(CompensationCalendarItem(
            id=c.id,
            teacher_id=c.teacher_id,
            teacher=c.teacher.name,
            class_section_id=c.class_section_id,
            class_section=c.class_section.name,
            subject=c.subject.name,
            date=on,
            day_of_week=on.weekday(),
            period_indexes=sorted(s.period_index for s in slots),
            periods=c.periods,
            room=c.room.name if c.room else None,
            status=c.status,
            is_lab=c.is_lab,
        ))
    return items


@router.post("/backfill", response_model=BackfillResult)
def backfill(db: Session = Depends(get_db), hod: Teacher = Depends(require_hod)):
    created, periods, skipped = svc.backfill(db, hod.id)
    db.commit()
    return BackfillResult(created=created, periods=periods, skipped=skipped)


@router.get("/{comp_id}/suggestions", response_model=list[CompensationSuggestionOut])
def suggestions(
    comp_id: int,
    db: Session = Depends(get_db),
    current: Teacher = Depends(get_current_teacher),
):
    comp = _get(db, comp_id, current)
    if comp.status not in ACTIVE:
        raise HTTPException(status_code=409, detail=f"This make-up is {comp.status.value.lower()}.")
    return [CompensationSuggestionOut(**vars(s)) for s in svc.suggest_slots(db, comp)]


def _notify(db: Session, comp: Compensation, title: str, body: str) -> None:
    svc.notify_teacher_and_hods(db, comp.teacher, title, body)


@router.post("/{comp_id}/confirm", response_model=CompensationOut)
def confirm(
    comp_id: int,
    payload: CompensationSlotRequest | None = None,
    db: Session = Depends(get_db),
    current: Teacher = Depends(get_current_teacher),
):
    comp = _get(db, comp_id, current)
    if comp.status != CompensationStatus.PROPOSED:
        raise HTTPException(status_code=409, detail="Only proposed make-ups can be confirmed.")
    if payload is not None:
        err = svc.apply_slot(db, comp, payload.date, payload.time_slot_id, payload.time_slot2_id, payload.room_id)
    elif comp.proposed_date is None or comp.proposed_time_slot_id is None:
        err = "No slot is proposed yet. Pick a slot first."
    else:
        room, err = svc.validate_slot(db, comp, comp.proposed_date, comp.proposed_time_slot_id,
                                      comp.proposed_time_slot2_id, comp.room_id)
        if err is None:
            comp.room_id = room
    if err:
        db.rollback()
        raise HTTPException(status_code=409, detail=err)
    comp.status = CompensationStatus.SCHEDULED
    comp.updated_at = _now()
    audit.log(db, actor_id=current.id, action="COMP_SCHEDULED", entity="compensation", entity_id=comp.id,
              detail=f"{comp.teacher.name}: {_slot_label(comp)}")
    _notify(db, comp, "Make-up class scheduled",
            f"{comp.subject.name} for {comp.class_section.name} on {_slot_label(comp)}.")
    db.commit()
    db.refresh(comp)
    return svc.to_out(comp)


@router.post("/{comp_id}/reschedule", response_model=CompensationOut)
def reschedule(
    comp_id: int,
    payload: CompensationSlotRequest,
    db: Session = Depends(get_db),
    current: Teacher = Depends(get_current_teacher),
):
    comp = _get(db, comp_id, current)
    if comp.status not in ACTIVE:
        raise HTTPException(status_code=409, detail="Only proposed or scheduled make-ups can be rescheduled.")
    err = svc.apply_slot(db, comp, payload.date, payload.time_slot_id, payload.time_slot2_id, payload.room_id)
    if err:
        db.rollback()
        raise HTTPException(status_code=409, detail=err)
    comp.status = CompensationStatus.SCHEDULED
    comp.notes = None if comp.notes == svc.NO_SLOT_NOTE else comp.notes
    comp.updated_at = _now()
    audit.log(db, actor_id=current.id, action="COMP_RESCHEDULED", entity="compensation", entity_id=comp.id,
              detail=f"{comp.teacher.name}: {_slot_label(comp)}")
    _notify(db, comp, "Make-up class rescheduled",
            f"{comp.subject.name} for {comp.class_section.name} is now on {_slot_label(comp)}.")
    db.commit()
    db.refresh(comp)
    return svc.to_out(comp)


@router.post("/{comp_id}/complete", response_model=CompensationOut)
def complete(
    comp_id: int,
    db: Session = Depends(get_db),
    current: Teacher = Depends(get_current_teacher),
):
    comp = _get(db, comp_id, current)
    if comp.status != CompensationStatus.SCHEDULED:
        raise HTTPException(status_code=409, detail="Only scheduled make-ups can be marked done.")
    if comp.proposed_date is None or comp.proposed_date > date.today():
        raise HTTPException(status_code=409, detail="The make-up has not taken place yet.")
    comp.status = CompensationStatus.COMPLETED
    comp.updated_at = _now()
    audit.log(db, actor_id=current.id, action="COMP_COMPLETED", entity="compensation", entity_id=comp.id,
              detail=f"{comp.teacher.name}: {comp.subject.name} ({comp.class_section.name})")
    _notify(db, comp, "Make-up class completed",
            f"{comp.subject.name} for {comp.class_section.name} was marked done.")
    db.commit()
    db.refresh(comp)
    return svc.to_out(comp)


@router.post("/{comp_id}/cancel", response_model=CompensationOut)
def cancel(
    comp_id: int,
    db: Session = Depends(get_db),
    current: Teacher = Depends(get_current_teacher),
):
    comp = _get(db, comp_id, current, hod_only=True)
    if comp.status not in ACTIVE:
        raise HTTPException(status_code=409, detail="Only proposed or scheduled make-ups can be cancelled.")
    comp.status = CompensationStatus.CANCELLED
    comp.updated_at = _now()
    audit.log(db, actor_id=current.id, action="COMP_CANCELLED", entity="compensation", entity_id=comp.id,
              detail=f"{comp.teacher.name}: {comp.subject.name} ({comp.class_section.name}) cancelled by HOD")
    _notify(db, comp, "Make-up class cancelled",
            f"The make-up for {comp.subject.name} ({comp.class_section.name}) was cancelled by the HOD.")
    db.commit()
    db.refresh(comp)
    return svc.to_out(comp)


@router.post("/{comp_id}/repropose", response_model=CompensationOut)
def repropose(
    comp_id: int,
    db: Session = Depends(get_db),
    current: Teacher = Depends(get_current_teacher),
):
    comp = _get(db, comp_id, current)
    if comp.status not in ACTIVE:
        raise HTTPException(status_code=409, detail="Only proposed or scheduled make-ups can be re-proposed.")
    found = svc.repropose(db, comp)
    audit.log(db, actor_id=current.id, action="COMP_PROPOSED", entity="compensation", entity_id=comp.id,
              detail="Re-proposed" + (f": {_slot_label(comp)}" if found else ": no slot found"))
    db.commit()
    db.refresh(comp)
    return svc.to_out(comp)
