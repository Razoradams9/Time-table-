"""Authentication routes (Requirement 1)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Teacher
from app.schemas import TeacherOut, Token
from app.security import create_access_token, get_current_teacher, verify_password

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/login", response_model=Token)
def login(form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    # OAuth2 form uses "username"; we treat it as the email.
    teacher = db.scalar(select(Teacher).where(Teacher.email == form.username))
    if teacher is None or not verify_password(form.password, teacher.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
        )
    if not teacher.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account is inactive.")
    token = create_access_token(teacher)
    return Token(
        access_token=token,
        role=teacher.role,
        teacher_id=teacher.id,
        name=teacher.name,
    )


@router.get("/me", response_model=TeacherOut)
def me(current: Teacher = Depends(get_current_teacher)):
    return current
