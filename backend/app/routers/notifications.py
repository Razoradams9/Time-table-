"""In-app notification endpoints (Requirement 8)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Notification, Teacher
from app.schemas import NotificationOut
from app.security import get_current_teacher

router = APIRouter(prefix="/api/notifications", tags=["notifications"])


@router.get("", response_model=list[NotificationOut])
def my_notifications(db: Session = Depends(get_db), current: Teacher = Depends(get_current_teacher)):
    return db.scalars(
        select(Notification)
        .where(Notification.teacher_id == current.id)
        .order_by(Notification.created_at.desc())
        .limit(100)
    ).all()


@router.get("/unread-count")
def unread_count(db: Session = Depends(get_db), current: Teacher = Depends(get_current_teacher)):
    count = db.scalar(
        select(func.count(Notification.id)).where(
            Notification.teacher_id == current.id, Notification.is_read.is_(False)
        )
    )
    return {"unread": count or 0}


@router.post("/{notification_id}/read", response_model=NotificationOut)
def mark_read(notification_id: int, db: Session = Depends(get_db), current: Teacher = Depends(get_current_teacher)):
    n = db.get(Notification, notification_id)
    if n is None or n.teacher_id != current.id:
        raise HTTPException(status_code=404, detail="Notification not found.")
    n.is_read = True
    db.commit()
    db.refresh(n)
    return n


@router.post("/read-all")
def mark_all_read(db: Session = Depends(get_db), current: Teacher = Depends(get_current_teacher)):
    unread = db.scalars(
        select(Notification).where(
            Notification.teacher_id == current.id, Notification.is_read.is_(False)
        )
    ).all()
    for n in unread:
        n.is_read = True
    db.commit()
    return {"marked": len(unread)}
