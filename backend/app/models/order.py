from __future__ import annotations

from sqlalchemy import Enum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, new_id

ORDER_STATUSES = ("pending_payment", "placed", "preparing", "ready", "completed", "cancelled")
PAYMENT_STATUSES = ("unpaid", "pending", "paid", "failed", "refunded")


class Order(TimestampMixin, Base):
    __tablename__ = "orders"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_id)
    order_number: Mapped[str] = mapped_column(String(40), unique=True, nullable=False, index=True)
    user_id: Mapped[str] = mapped_column(String, ForeignKey("users.id"), nullable=False, index=True)
    status: Mapped[str] = mapped_column(
        Enum(*ORDER_STATUSES, name="order_status"), default="placed", nullable=False
    )
    subtotal_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    total_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    cart_id: Mapped[str | None] = mapped_column(
        String, ForeignKey("carts.id"), nullable=True, index=True
    )
    # Attribution: copied from the originating cart at checkout so a sale can be traced
    # back to the AI chat that drove it.
    conversation_id: Mapped[str | None] = mapped_column(
        String, ForeignKey("conversations.id"), nullable=True, index=True
    )
    source: Mapped[str | None] = mapped_column(String(16), nullable=True, default="web", index=True)
    stripe_payment_intent_id: Mapped[str | None] = mapped_column(
        String(255), nullable=True, index=True
    )
    payment_status: Mapped[str] = mapped_column(
        Enum(*PAYMENT_STATUSES, name="payment_status"), default="unpaid", nullable=False
    )
    amount_paid_cents: Mapped[int | None] = mapped_column(Integer, nullable=True)
    currency: Mapped[str] = mapped_column(String(3), default="cad", nullable=False)

    user = relationship("User", back_populates="orders")
    items: Mapped[list["OrderItem"]] = relationship(
        back_populates="order", cascade="all, delete-orphan"
    )

    @property
    def total(self) -> float:
        return self.total_cents / 100


class OrderItem(Base):
    __tablename__ = "order_items"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_id)
    order_id: Mapped[str] = mapped_column(
        String, ForeignKey("orders.id", ondelete="CASCADE"), nullable=False
    )
    menu_item_id: Mapped[str | None] = mapped_column(String, nullable=True)
    # Snapshot fields — frozen at checkout so later menu edits don't change history
    name_snapshot: Mapped[str] = mapped_column(String(200), nullable=False)
    unit_price_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    line_total_cents: Mapped[int] = mapped_column(Integer, nullable=False)

    order: Mapped[Order] = relationship(back_populates="items")
    options: Mapped[list["OrderItemOption"]] = relationship(
        back_populates="order_item", cascade="all, delete-orphan"
    )


class OrderItemOption(Base):
    __tablename__ = "order_item_options"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_id)
    order_item_id: Mapped[str] = mapped_column(
        String, ForeignKey("order_items.id", ondelete="CASCADE"), nullable=False
    )
    name_snapshot: Mapped[str] = mapped_column(String(100), nullable=False)
    price_delta_cents: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    order_item: Mapped[OrderItem] = relationship(back_populates="options")
