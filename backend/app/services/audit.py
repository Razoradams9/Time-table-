"""Audit logging helper (Requirement 9)."""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.models import AuditLog


def log(
    db: Session,
    *,
    actor_id: int | None,
    action: str,
    entity: str,
    entity_id: int | None = None,
    detail: str | None = None,
) -> AuditLog:
    entry = AuditLog(
        actor_id=actor_id,
        action=action,
        entity=entity,
        entity_id=entity_id,
        detail=detail,
    )
    db.add(entry)
    return entry
