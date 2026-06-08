from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, new_id


class User(TimestampMixin, Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_id)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    role: Mapped[str] = mapped_column(
        Enum("customer", "admin", name="user_role"), nullable=False, default="customer"
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    refresh_tokens: Mapped[list["RefreshToken"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    carts: Mapped[list["Cart"]] = relationship(back_populates="user")  # noqa: F821
    orders: Mapped[list["Order"]] = relationship(back_populates="user")  # noqa: F821
    conversations: Mapped[list["Conversation"]] = relationship(back_populates="user")  # noqa: F821
    preferences: Mapped[list["UserPreference"]] = relationship(  # noqa: F821
        "UserPreference", cascade="all, delete-orphan", foreign_keys="UserPreference.user_id"
    )


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(
        String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    jti: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    token_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    user: Mapped[User] = relationship(back_populates="refresh_tokens", foreign_keys=[user_id])
