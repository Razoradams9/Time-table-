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
    PasswordResetOut,
    RoomOut,
    SubjectOut,
    TeacherCreate,
    TeacherCreatedOut,
    TeacherOut,
    TimeSlotOut,
)
from app.security import (
    generate_password,
    get_current_teacher,
    hash_password,
    require_hod,
)
from app.services import audit
from fastapi import HTTPException, status

router = APIRouter(prefix="/api/reference", tags=["reference"])


@router.get("/time-slots", response_model=list[TimeSlotOut])
def time_slots(db: Session = Depends(get_db), current: Teacher = Depends(get_current_teacher)):
    return db.scalars(select(TimeSlot).order_by(TimeSlot.day_of_week, TimeSlot.period_index)).all()


@router.get("/teachers", response_model=list[TeacherOut])
def teachers(db: Session = Depends(get_db), hod: Teacher = Depends(require_hod)):
    return db.scalars(select(Teacher).order_by(Teacher.name)).all()


@router.post("/teachers", response_model=TeacherCreatedOut, status_code=status.HTTP_201_CREATED)
def create_teacher(
    payload: TeacherCreate,
    db: Session = Depends(get_db),
    hod: Teacher = Depends(require_hod),
):
    email = payload.email.strip().lower()
    if db.scalar(select(Teacher).where(Teacher.email == email)):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A teacher with that email already exists.",
        )
    initial_password = payload.initial_password or generate_password()
    teacher = Teacher(
        name=payload.name.strip(),
        email=email,
        hashed_password=hash_password(initial_password),
        role=payload.role,
        department_id=payload.department_id,
        max_periods_per_day=payload.max_periods_per_day,
        is_active=True,
        must_change_password=True,
    )
    db.add(teacher)
    db.flush()
    audit.log(
        db,
        actor_id=hod.id,
        action="CREATE_TEACHER",
        entity="Teacher",
        entity_id=teacher.id,
        detail=f"Created account for {teacher.email}.",
    )
    db.commit()
    db.refresh(teacher)
    return TeacherCreatedOut(
        id=teacher.id,
        name=teacher.name,
        email=teacher.email,
        role=teacher.role,
        initial_password=initial_password,
    )


@router.post("/teachers/{teacher_id}/deactivate", response_model=TeacherOut)
def deactivate_teacher(
    teacher_id: int,
    db: Session = Depends(get_db),
    hod: Teacher = Depends(require_hod),
):
    teacher = db.get(Teacher, teacher_id)
    if teacher is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Teacher not found.")
    if teacher.id == hod.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot deactivate your own account.",
        )
    teacher.is_active = False
    audit.log(
        db,
        actor_id=hod.id,
        action="DEACTIVATE_TEACHER",
        entity="Teacher",
        entity_id=teacher.id,
        detail=f"Deactivated {teacher.email}.",
    )
    db.commit()
    db.refresh(teacher)
    return teacher


@router.post("/teachers/{teacher_id}/activate", response_model=TeacherOut)
def activate_teacher(
    teacher_id: int,
    db: Session = Depends(get_db),
    hod: Teacher = Depends(require_hod),
):
    teacher = db.get(Teacher, teacher_id)
    if teacher is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Teacher not found.")
    teacher.is_active = True
    audit.log(
        db,
        actor_id=hod.id,
        action="ACTIVATE_TEACHER",
        entity="Teacher",
        entity_id=teacher.id,
        detail=f"Reactivated {teacher.email}.",
    )
    db.commit()
    db.refresh(teacher)
    return teacher


@router.post("/teachers/{teacher_id}/reset-password", response_model=PasswordResetOut)
def reset_teacher_password(
    teacher_id: int,
    db: Session = Depends(get_db),
    hod: Teacher = Depends(require_hod),
):
    teacher = db.get(Teacher, teacher_id)
    if teacher is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Teacher not found.")
    new_password = generate_password()
    teacher.hashed_password = hash_password(new_password)
    teacher.must_change_password = True
    audit.log(
        db,
        actor_id=hod.id,
        action="RESET_PASSWORD",
        entity="Teacher",
        entity_id=teacher.id,
        detail=f"Reset password for {teacher.email}.",
    )
    db.commit()
    return PasswordResetOut(
        teacher_id=teacher.id,
        email=teacher.email,
        new_password=new_password,
    )


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
