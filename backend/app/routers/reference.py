"""Reference data endpoints for populating UI (teachers, subjects, slots, etc.)."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import (
    ClassSection,
    Department,
    Room,
    Subject,
    Teacher,
    TimeSlot,
)
from app.schemas import (
    ClassSectionOut,
    DepartmentOut,
    RoomOut,
    SubjectOut,
    TeacherOut,
    TimeSlotOut,
)
from app.security import get_current_teacher, require_hod

router = APIRouter(prefix="/api/reference", tags=["reference"])


@router.get("/time-slots", response_model=list[TimeSlotOut])
def time_slots(db: Session = Depends(get_db), current: Teacher = Depends(get_current_teacher)):
    return db.scalars(select(TimeSlot).order_by(TimeSlot.day_of_week, TimeSlot.period_index)).all()


@router.get("/teachers", response_model=list[TeacherOut])
def teachers(db: Session = Depends(get_db), hod: Teacher = Depends(require_hod)):
    return db.scalars(select(Teacher).order_by(Teacher.name)).all()


@router.get("/subjects", response_model=list[SubjectOut])
def subjects(db: Session = Depends(get_db), hod: Teacher = Depends(require_hod)):
    return db.scalars(select(Subject).order_by(Subject.name)).all()


@router.get("/classes", response_model=list[ClassSectionOut])
def classes(db: Session = Depends(get_db), hod: Teacher = Depends(require_hod)):
    return db.scalars(select(ClassSection).order_by(ClassSection.name)).all()


@router.get("/rooms", response_model=list[RoomOut])
def rooms(db: Session = Depends(get_db), hod: Teacher = Depends(require_hod)):
    return db.scalars(select(Room).order_by(Room.name)).all()


@router.get("/departments", response_model=list[DepartmentOut])
def departments(db: Session = Depends(get_db), hod: Teacher = Depends(require_hod)):
    return db.scalars(select(Department).order_by(Department.name)).all()
