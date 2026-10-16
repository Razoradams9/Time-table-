"""HOD-only teacher account management (Tier-1 security).

Create accounts (with an auto-generated temp password the HOD hands over),
reset passwords, enable/disable, and edit basic details. New accounts and
resets set must_change_password so the teacher is forced to set their own
password on first login.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Role, Subject, Teacher
from app.schemas import (
    PasswordReset,
    TeacherCreate,
    TeacherCreated,
    TeacherOut,
    TeacherUpdate,
)
from app.security import generate_temp_password, hash_password, require_hod
from app.services import audit

router = APIRouter(prefix="/api/accounts", tags=["accounts"])


def _apply_subjects(db: Session, teacher: Teacher, subject_ids: list[int]) -> None:
    subs = db.scalars(select(Subject).where(Subject.id.in_(subject_ids))).all() if subject_ids else []
    teacher.subjects = subs


@router.get("", response_model=list[TeacherOut])
def list_accounts(db: Session = Depends(get_db), hod: Teacher = Depends(require_hod)):
    return db.scalars(select(Teacher).order_by(Teacher.name)).all()


@router.post("", response_model=TeacherCreated)
def create_account(payload: TeacherCreate, db: Session = Depends(get_db), hod: Teacher = Depends(require_hod)):
    existing = db.scalar(select(Teacher).where(Teacher.email == payload.email))
    if existing:
        raise HTTPException(status_code=409, detail="A teacher with that email already exists.")

    temp = generate_temp_password()
    teacher = Teacher(
        name=payload.name,
        email=payload.email,
        hashed_password=hash_password(temp),
        role=payload.role,
        department_id=payload.department_id,
        max_periods_per_day=payload.max_periods_per_day,
        is_active=True,
        must_change_password=True,
    )
    db.add(teacher)
    db.flush()
    _apply_subjects(db, teacher, payload.subject_ids)
    audit.log(db, actor_id=hod.id, action="CREATE", entity="teacher", entity_id=teacher.id,
              detail=f"Account for {payload.email}")
    db.commit()
    db.refresh(teacher)
    return TeacherCreated(id=teacher.id, name=teacher.name, email=teacher.email, temp_password=temp)


@router.patch("/{teacher_id}", response_model=TeacherOut)
def update_account(teacher_id: int, payload: TeacherUpdate, db: Session = Depends(get_db),
                   hod: Teacher = Depends(require_hod)):
    teacher = db.get(Teacher, teacher_id)
    if teacher is None:
        raise HTTPException(status_code=404, detail="Teacher not found.")
    if payload.name is not None:
        teacher.name = payload.name
    if payload.department_id is not None:
        teacher.department_id = payload.department_id
    if payload.max_periods_per_day is not None:
        teacher.max_periods_per_day = payload.max_periods_per_day
    if payload.is_active is not None:
        # Don't let the HOD disable their own account by accident.
        if teacher.id == hod.id and not payload.is_active:
            raise HTTPException(status_code=400, detail="You cannot disable your own account.")
        teacher.is_active = payload.is_active
    if payload.subject_ids is not None:
        _apply_subjects(db, teacher, payload.subject_ids)
    audit.log(db, actor_id=hod.id, action="UPDATE", entity="teacher", entity_id=teacher.id)
    db.commit()
    db.refresh(teacher)
    return teacher


@router.post("/{teacher_id}/reset-password", response_model=PasswordReset)
def reset_password(teacher_id: int, db: Session = Depends(get_db), hod: Teacher = Depends(require_hod)):
    teacher = db.get(Teacher, teacher_id)
    if teacher is None:
        raise HTTPException(status_code=404, detail="Teacher not found.")
    temp = generate_temp_password()
    teacher.hashed_password = hash_password(temp)
    teacher.must_change_password = True
    audit.log(db, actor_id=hod.id, action="RESET_PASSWORD", entity="teacher", entity_id=teacher.id)
    db.commit()
    return PasswordReset(temp_password=temp)
