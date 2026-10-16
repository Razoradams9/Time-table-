"""Timetable generation, approval, and viewing (Requirements 2 & 3)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import ClassSection, Role, Teacher, TimetableEntry
from app.schemas import (
    ClassSectionOut,
    GenerationResult,
    TeacherOut,
    TimetableEntryOut,
)
from app.security import get_current_teacher, require_hod
from app.services import audit
from app.services.timetable_generator import generate_timetable

router = APIRouter(prefix="/api/timetable", tags=["timetable"])


@router.get("/view/options")
def view_options(db: Session = Depends(get_db), current: Teacher = Depends(get_current_teacher)):
    """Teachers and classes to populate the two timetable-view pickers.
    Available to any logged-in user (both views are read-only)."""
    teachers = db.scalars(select(Teacher).order_by(Teacher.name)).all()
    classes = db.scalars(select(ClassSection).order_by(ClassSection.name)).all()
    return {
        "teachers": [TeacherOut.model_validate(t, from_attributes=True) for t in teachers],
        "classes": [ClassSectionOut.model_validate(c, from_attributes=True) for c in classes],
    }


@router.get("/view/teacher/{teacher_id}", response_model=list[TimetableEntryOut])
def teacher_view(teacher_id: int, db: Session = Depends(get_db), current: Teacher = Depends(get_current_teacher)):
    """Teacher-wise timetable: every period this teacher leads or co-teaches."""
    return db.scalars(
        select(TimetableEntry).where(
            TimetableEntry.is_active.is_(True),
            (TimetableEntry.teacher_id == teacher_id)
            | (TimetableEntry.co_teacher_id == teacher_id),
        )
    ).all()


@router.get("/view/class/{class_id}", response_model=list[TimetableEntryOut])
def class_view(class_id: int, db: Session = Depends(get_db), current: Teacher = Depends(get_current_teacher)):
    """Stream-wise timetable: every period for a class/section."""
    return db.scalars(
        select(TimetableEntry).where(
            TimetableEntry.is_active.is_(True),
            TimetableEntry.class_section_id == class_id,
        )
    ).all()


@router.post("/generate", response_model=GenerationResult)
def generate(db: Session = Depends(get_db), hod: Teacher = Depends(require_hod)):
    outcome = generate_timetable(db)
    if outcome.success:
        audit.log(db, actor_id=hod.id, action="GENERATE", entity="timetable",
                  entity_id=outcome.version, detail=outcome.message)
        db.commit()
    return GenerationResult(
        success=outcome.success,
        version=outcome.version,
        entries=outcome.entries,
        message=outcome.message,
        conflicts=outcome.conflicts,
    )


@router.post("/approve/{version}", response_model=GenerationResult)
def approve(version: int, db: Session = Depends(get_db), hod: Teacher = Depends(require_hod)):
    entries = db.scalars(select(TimetableEntry).where(TimetableEntry.version == version)).all()
    if not entries:
        raise HTTPException(status_code=404, detail=f"No timetable version {version} found.")
    # Deactivate all, then activate this version -> locks it as the base (Req 2.7).
    for e in db.scalars(select(TimetableEntry)).all():
        e.is_active = e.version == version
    audit.log(db, actor_id=hod.id, action="APPROVE", entity="timetable", entity_id=version,
              detail=f"Locked v{version} as active base timetable.")
    db.commit()
    return GenerationResult(success=True, version=version, entries=len(entries),
                            message=f"Timetable v{version} is now the active base.")


@router.get("/versions")
def versions(db: Session = Depends(get_db), hod: Teacher = Depends(require_hod)):
    rows = db.execute(
        select(TimetableEntry.version, TimetableEntry.is_active).distinct()
    ).all()
    seen: dict[int, bool] = {}
    for version, is_active in rows:
        seen[version] = seen.get(version, False) or is_active
    return [{"version": v, "is_active": a} for v, a in sorted(seen.items(), reverse=True)]


@router.get("/active", response_model=list[TimetableEntryOut])
def active_timetable(db: Session = Depends(get_db), current: Teacher = Depends(get_current_teacher)):
    """Full active base timetable. HOD sees all; teachers see only their own."""
    stmt = select(TimetableEntry).where(TimetableEntry.is_active.is_(True))
    if current.role != Role.HOD:
        stmt = stmt.where(TimetableEntry.teacher_id == current.id)
    return db.scalars(stmt).all()


@router.get("/version/{version}", response_model=list[TimetableEntryOut])
def timetable_by_version(version: int, db: Session = Depends(get_db), hod: Teacher = Depends(require_hod)):
    return db.scalars(select(TimetableEntry).where(TimetableEntry.version == version)).all()
