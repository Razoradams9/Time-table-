"""Authentication routes (Requirement 1)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Teacher
from app.schemas import ChangePassword, TeacherOut, Token
from app.security import (
    create_access_token,
    get_current_teacher,
    hash_password,
    validate_password_strength,
    verify_password,
)
from app.services import audit

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
        must_change_password=teacher.must_change_password,
    )


@router.get("/me", response_model=TeacherOut)
def me(current: Teacher = Depends(get_current_teacher)):
    return current


@router.post("/change-password")
def change_password(
    payload: ChangePassword,
    db: Session = Depends(get_db),
    current: Teacher = Depends(get_current_teacher),
):
    """A teacher changes their own password (also clears the forced-change flag)."""
    if not verify_password(payload.current_password, current.hashed_password):
        raise HTTPException(status_code=400, detail="Current password is incorrect.")
    err = validate_password_strength(payload.new_password)
    if err:
        raise HTTPException(status_code=400, detail=err)
    if verify_password(payload.new_password, current.hashed_password):
        raise HTTPException(status_code=400, detail="New password must differ from the current one.")
    current.hashed_password = hash_password(payload.new_password)
    current.must_change_password = False
    audit.log(db, actor_id=current.id, action="CHANGE_PASSWORD", entity="teacher", entity_id=current.id)
    db.commit()
    return {"status": "ok", "message": "Password changed."}
