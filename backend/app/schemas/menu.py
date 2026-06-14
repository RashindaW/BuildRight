from __future__ import annotations

from pydantic import BaseModel, Field

from app.schemas.common import ORMBase


class OptionChoiceOut(ORMBase):
    id: str
    name: str
    price_delta_cents: int
    is_default: bool
    is_available: bool


class OptionGroupOut(ORMBase):
    id: str
    name: str
    min_select: int
    max_select: int
    required: bool
    choices: list[OptionChoiceOut]


class MenuItemOut(BaseModel):
    id: str
    slug: str
    sku: str | None = None
    name: str
    description: str
    price: float
    price_cents: int
    category: str
    is_available: bool
    stock_qty: int = 0
    featured: bool
    image_url: str | None
    dietary_tags: list[str]
    allergens: list[str]
    keywords: list[str]
    calories: int | None
    spice_level: int
    prep_time_min: int | None
    option_groups: list[OptionGroupOut] = []

    @classmethod
    def from_model(cls, item) -> "MenuItemOut":
        return cls(
            id=item.id,
            slug=item.slug,
            sku=item.sku,
            name=item.name,
            description=item.description,
            price=item.price_cents / 100,
            price_cents=item.price_cents,
            category=item.category.slug,
            is_available=item.is_available,
            stock_qty=item.stock_qty,
            featured=item.featured,
            image_url=item.image_url,
            dietary_tags=sorted(t.slug for t in item.dietary_tags),
            allergens=sorted(a.slug for a in item.allergens),
            keywords=list(item.keywords or []),
            calories=item.calories,
            spice_level=item.spice_level,
            prep_time_min=item.prep_time_min,
            option_groups=[OptionGroupOut.model_validate(g) for g in item.option_groups],
        )


class MenuItemCreate(BaseModel):
    model_config = {"extra": "forbid"}
    slug: str = Field(min_length=1, max_length=100)
    name: str = Field(min_length=1, max_length=200)
    description: str = ""
    price_cents: int = Field(ge=0)
    cost_cents: int | None = Field(default=None, ge=0)
    category: str
    dietary_tags: list[str] = []
    allergens: list[str] = []
    keywords: list[str] = []
    calories: int | None = None
    spice_level: int = Field(default=0, ge=0, le=3)
    prep_time_min: int | None = None
    is_available: bool = True
    featured: bool = False
    image_url: str | None = None


class MenuItemUpdate(BaseModel):
    model_config = {"extra": "forbid"}
    name: str | None = None
    description: str | None = None
    price_cents: int | None = Field(default=None, ge=0)
    cost_cents: int | None = Field(default=None, ge=0)
    category: str | None = None
    dietary_tags: list[str] | None = None
    allergens: list[str] | None = None
    keywords: list[str] | None = None
    calories: int | None = None
    spice_level: int | None = Field(default=None, ge=0, le=3)
    prep_time_min: int | None = None
    is_available: bool | None = None
    featured: bool | None = None
    image_url: str | None = None


class CategoryOut(ORMBase):
    id: str
    slug: str
    name: str
    display_order: int
