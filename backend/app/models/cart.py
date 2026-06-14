from __future__ import annotations

from sqlalchemy import Enum, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, new_id


class Cart(TimestampMixin, Base):
    __tablename__ = "carts"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_id)
    user_id: Mapped[str | None] = mapped_column(
        String, ForeignKey("users.id"), nullable=True, index=True
    )
    session_id: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    status: Mapped[str] = mapped_column(
        Enum("active", "converted", "abandoned", name="cart_status"),
        default="active",
        nullable=False,
    )
    # Attribution: which chat conversation (if any) drove items into this cart, and the
    # channel the cart was last touched through ("web" | "chat" | "voice").
    conversation_id: Mapped[str | None] = mapped_column(
        String, ForeignKey("conversations.id"), nullable=True, index=True
    )
    source: Mapped[str | None] = mapped_column(String(16), nullable=True, default="web")

    user = relationship("User", back_populates="carts")
    items: Mapped[list["CartItem"]] = relationship(
        back_populates="cart", cascade="all, delete-orphan"
    )


class CartItem(Base):
    __tablename__ = "cart_items"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_id)
    cart_id: Mapped[str] = mapped_column(
        String, ForeignKey("carts.id", ondelete="CASCADE"), nullable=False
    )
    menu_item_id: Mapped[str] = mapped_column(
        String, ForeignKey("menu_items.id"), nullable=False
    )
    quantity: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

    cart: Mapped[Cart] = relationship(back_populates="items")
    menu_item = relationship("MenuItem")
    options: Mapped[list["CartItemOption"]] = relationship(
        back_populates="cart_item", cascade="all, delete-orphan"
    )


class CartItemOption(Base):
    __tablename__ = "cart_item_options"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_id)
    cart_item_id: Mapped[str] = mapped_column(
        String, ForeignKey("cart_items.id", ondelete="CASCADE"), nullable=False
    )
    option_choice_id: Mapped[str] = mapped_column(
        String, ForeignKey("option_choices.id"), nullable=False
    )

    cart_item: Mapped[CartItem] = relationship(back_populates="options")
    option_choice = relationship("OptionChoice")
