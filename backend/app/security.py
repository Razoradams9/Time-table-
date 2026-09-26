"""Password hashing and JWT helpers, plus auth dependencies."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import bcrypt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models import Role, Teacher

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


def hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
    except ValueError:
        return False


def create_access_token(teacher: Teacher) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.access_token_expire_minutes)
    payload = {
        "sub": str(teacher.id),
        "role": teacher.role.value,
        "name": teacher.name,
        "exp": expire,
    }
    return jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)


def get_current_teacher(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> Teacher:
    credentials_exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        teacher_id = payload.get("sub")
        if teacher_id is None:
            raise credentials_exc
    except JWTError:
        raise credentials_exc

    teacher = db.get(Teacher, int(teacher_id))
    if teacher is None or not teacher.is_active:
        raise credentials_exc
    return teacher


def require_hod(current: Teacher = Depends(get_current_teacher)) -> Teacher:
    if current.role != Role.HOD:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This action requires HOD/Admin privileges.",
        )
    return current
