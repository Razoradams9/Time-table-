"""Authentication routes (Requirement 1)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import func, select
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
from app.services import audit, login_throttle

router = APIRouter(prefix="/api/auth", tags=["auth"])


# Verified against when the email is unknown, so timing matches a wrong password.
_DUMMY_HASH = hash_password("not-a-real-password")


@router.post("/login", response_model=Token)
def login(request: Request, form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    # OAuth2 form uses "username"; we treat it as the email.
    email = form.username.strip().lower()
    key = (email, request.client.host if request.client else "unknown")
    wait = login_throttle.retry_after(key)
    if wait > 0:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Too many failed sign-in attempts. Try again in {max(1, -(-wait // 60))} minute(s).",
            headers={"Retry-After": str(wait)},
        )
    teacher = db.scalar(select(Teacher).where(func.lower(Teacher.email) == email))
    if teacher is None:
        verify_password(form.password, _DUMMY_HASH)
        ok = False
    else:
        ok = verify_password(form.password, teacher.hashed_password)
    if not ok:
        login_throttle.record_failure(key)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
        )
    login_throttle.reset(key)
    if not teacher.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This account has been disabled. Contact your HOD.",
        )
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
