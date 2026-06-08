"""User preference persistence (user_preferences table)."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.user_memory import UserPreference


def get_preferences(db: Session, user_id: str) -> dict[str, str]:
    rows = db.execute(
        select(UserPreference).where(UserPreference.user_id == user_id)
    ).scalars().all()
    return {r.key: r.value for r in rows}


def set_preference(
    db: Session, user_id: str, key: str, value: str, source: str = "chat"
) -> UserPreference:
    pref = db.execute(
        select(UserPreference).where(
            UserPreference.user_id == user_id,
            UserPreference.key == key,
        )
    ).scalar_one_or_none()
    if pref is None:
        pref = UserPreference(user_id=user_id, key=key, value=value, source=source)
        db.add(pref)
    else:
        pref.value = value
        pref.source = source
    db.commit()
    db.refresh(pref)
    return pref
