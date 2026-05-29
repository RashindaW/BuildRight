from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.audit import AuditLog


def log(
    db: Session,
    action: str,
    actor_id: str | None = None,
    target: str | None = None,
    detail: dict | None = None,
    ip: str | None = None,
    note: str | None = None,
    commit: bool = True,
) -> None:
    entry = AuditLog(
        actor_id=actor_id, action=action, target=target, detail=detail, ip=ip, note=note
    )
    db.add(entry)
    if commit:
        db.commit()
