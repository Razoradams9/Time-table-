"""Notification service: in-app records + email (Requirement 8).

If SMTP is not configured, emails are logged to the console so the system is
fully usable in development without external services.
"""
from __future__ import annotations

import logging
import smtplib
from email.mime.text import MIMEText

from sqlalchemy.orm import Session

from app.config import settings
from app.models import Notification, Teacher

logger = logging.getLogger("notifications")


def _send_email(to_email: str, subject: str, body: str) -> None:
    if not settings.smtp_host:
        logger.info("[EMAIL:console] to=%s subject=%s\n%s", to_email, subject, body)
        return
    try:
        msg = MIMEText(body)
        msg["Subject"] = subject
        msg["From"] = settings.smtp_from
        msg["To"] = to_email
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as server:
            server.starttls()
            if settings.smtp_user:
                server.login(settings.smtp_user, settings.smtp_password)
            server.sendmail(settings.smtp_from, [to_email], msg.as_string())
    except Exception:  # pragma: no cover - email must never break the flow
        logger.exception("Failed sending email to %s", to_email)


def notify(db: Session, teacher: Teacher, title: str, body: str) -> Notification:
    """Create an in-app notification and dispatch an email."""
    n = Notification(teacher_id=teacher.id, title=title, body=body)
    db.add(n)
    _send_email(teacher.email, title, body)
    return n
