from __future__ import annotations

from sqlalchemy import Boolean, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, new_id


class Review(TimestampMixin, Base):
    """A customer's 1-5 star rating + optional comment for a product.

    One review per logged-in user per product (guests, with a NULL user_id, are not
    constrained). `sentiment` is derived from the rating; `verified_purchase` is set when
    the author has actually ordered the item.
    """

    __tablename__ = "reviews"
    __table_args__ = (UniqueConstraint("menu_item_id", "user_id", name="uq_review_item_user"),)

    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_id)
    menu_item_id: Mapped[str] = mapped_column(
        String, ForeignKey("menu_items.id", ondelete="CASCADE"), nullable=False, index=True
    )
    rating: Mapped[int] = mapped_column(Integer, nullable=False)  # 1..5
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    author_name: Mapped[str] = mapped_column(String(80), nullable=False, default="Anonymous")
    user_id: Mapped[str | None] = mapped_column(
        String, ForeignKey("users.id"), nullable=True, index=True
    )
    session_id: Mapped[str | None] = mapped_column(String, nullable=True)
    sentiment: Mapped[str] = mapped_column(String(12), nullable=False, default="neutral")
    verified_purchase: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
