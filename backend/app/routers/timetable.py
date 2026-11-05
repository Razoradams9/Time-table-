"""Timetable generation, approval, and viewing (Requirements 2 & 3)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import ClassSection, Role, Teacher, TimetableEntry
from app.schemas import (
    ClassSectionOut,
    GenerationResult,
    TeacherOut,
    TimetableEntryOut,
)
from app.security import forbid, get_current_teacher, is_hod, require_hod
from app.services import audit
from app.services.timetable_generator import generate_timetable

router = APIRouter(prefix="/api/timetable", tags=["timetable"])


def _taught_class_ids(teacher_id: int):
    """Subquery: classes in which the teacher leads or co-teaches an active entry."""
    return select(TimetableEntry.class_section_id).where(
        TimetableEntry.is_active.is_(True),
        or_(TimetableEntry.teacher_id == teacher_id, TimetableEntry.co_teacher_id == teacher_id),
    )


@router.get("/view/options")
def view_options(db: Session = Depends(get_db), current: Teacher = Depends(get_current_teacher)):
    """Teachers and classes to populate the timetable-view pickers.
    HOD gets everyone; a teacher gets only themself and the classes they teach."""
    if is_hod(current):
        teachers = db.scalars(select(Teacher).order_by(Teacher.name)).all()
        classes = db.scalars(select(ClassSection).order_by(ClassSection.name)).all()
    else:
        teachers = [current]
        classes = db.scalars(
            select(ClassSection)
            .where(ClassSection.id.in_(_taught_class_ids(current.id)))
            .order_by(ClassSection.name)
        ).all()
    return {
        "teachers": [TeacherOut.model_validate(t, from_attributes=True) for t in teachers],
        "classes": [ClassSectionOut.model_validate(c, from_attributes=True) for c in classes],
    }


@router.get("/view/teacher/{teacher_id}", response_model=list[TimetableEntryOut])
def teacher_view(teacher_id: int, db: Session = Depends(get_db), current: Teacher = Depends(get_current_teacher)):
    """Teacher-wise timetable: every period this teacher leads or co-teaches.
    A teacher may only request their own."""
    if not is_hod(current) and teacher_id != current.id:
        forbid("You can only view your own timetable.")
    return db.scalars(
        select(TimetableEntry).where(
            TimetableEntry.is_active.is_(True),
            (TimetableEntry.teacher_id == teacher_id)
            | (TimetableEntry.co_teacher_id == teacher_id),
        )
    ).all()


@router.get("/view/class/{class_id}", response_model=list[TimetableEntryOut])
def class_view(class_id: int, db: Session = Depends(get_db), current: Teacher = Depends(get_current_teacher)):
    """Stream-wise timetable: every period for a class/section.
    A teacher may only request a class they teach."""
    if not is_hod(current) and class_id not in set(db.scalars(_taught_class_ids(current.id)).all()):
        forbid("You can only view classes you teach.")
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
