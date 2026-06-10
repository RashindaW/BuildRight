from __future__ import annotations

from sqlalchemy import (
    Boolean, Column, ForeignKey, Integer, JSON, String, Table, Text, UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, new_id

# ---- Association tables -------------------------------------------------

menuitem_dietarytag = Table(
    "menuitem_dietarytag",
    Base.metadata,
    Column("menu_item_id", String, ForeignKey("menu_items.id", ondelete="CASCADE"), primary_key=True),
    Column("dietary_tag_id", String, ForeignKey("dietary_tags.id", ondelete="CASCADE"), primary_key=True),
)

menuitem_allergen = Table(
    "menuitem_allergen",
    Base.metadata,
    Column("menu_item_id", String, ForeignKey("menu_items.id", ondelete="CASCADE"), primary_key=True),
    Column("allergen_id", String, ForeignKey("allergens.id", ondelete="CASCADE"), primary_key=True),
)


# ---- Lookup tables ------------------------------------------------------

class Category(Base):
    __tablename__ = "categories"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_id)
    slug: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    display_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    menu_items: Mapped[list["MenuItem"]] = relationship(back_populates="category")


class DietaryTag(Base):
    __tablename__ = "dietary_tags"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_id)
    slug: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    label: Mapped[str] = mapped_column(String(100), nullable=False)

    menu_items: Mapped[list["MenuItem"]] = relationship(
        secondary=menuitem_dietarytag, back_populates="dietary_tags"
    )


class Allergen(Base):
    __tablename__ = "allergens"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_id)
    slug: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    label: Mapped[str] = mapped_column(String(100), nullable=False)

    menu_items: Mapped[list["MenuItem"]] = relationship(
        secondary=menuitem_allergen, back_populates="allergens"
    )


# ---- MenuItem -----------------------------------------------------------

class MenuItem(TimestampMixin, Base):
    __tablename__ = "menu_items"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_id)
    slug: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    sku: Mapped[str | None] = mapped_column(String(32), unique=True, nullable=True, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    price_cents: Mapped[int] = mapped_column(Integer, nullable=False)  # integer cents
    category_id: Mapped[str] = mapped_column(
        String, ForeignKey("categories.id"), nullable=False, index=True
    )
    is_available: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    stock_qty: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    featured: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    image_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    keywords: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    calories: Mapped[int | None] = mapped_column(Integer, nullable=True)
    spice_level: Mapped[int] = mapped_column(Integer, default=0, nullable=False)  # 0-3
    prep_time_min: Mapped[int | None] = mapped_column(Integer, nullable=True)

    category: Mapped[Category] = relationship(back_populates="menu_items")
    dietary_tags: Mapped[list[DietaryTag]] = relationship(
        secondary=menuitem_dietarytag, back_populates="menu_items"
    )
    allergens: Mapped[list[Allergen]] = relationship(
        secondary=menuitem_allergen, back_populates="menu_items"
    )
    option_groups: Mapped[list["OptionGroup"]] = relationship(
        back_populates="menu_item", cascade="all, delete-orphan"
    )

    @property
    def price(self) -> float:
        return self.price_cents / 100


class OptionGroup(Base):
    __tablename__ = "option_groups"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_id)
    menu_item_id: Mapped[str] = mapped_column(
        String, ForeignKey("menu_items.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    min_select: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    max_select: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    required: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    menu_item: Mapped[MenuItem] = relationship(back_populates="option_groups")
    choices: Mapped[list["OptionChoice"]] = relationship(
        back_populates="option_group", cascade="all, delete-orphan"
    )


class OptionChoice(Base):
    __tablename__ = "option_choices"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_id)
    option_group_id: Mapped[str] = mapped_column(
        String, ForeignKey("option_groups.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    price_delta_cents: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_available: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    option_group: Mapped[OptionGroup] = relationship(back_populates="choices")
