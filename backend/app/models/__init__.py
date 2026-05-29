"""Import all models so SQLAlchemy metadata + Alembic see them."""

from app.models.audit import AuditLog
from app.models.base import Base
from app.models.cart import Cart, CartItem, CartItemOption
from app.models.chat import Conversation, Message
from app.models.menu import (
    Allergen,
    Category,
    DietaryTag,
    MenuItem,
    OptionChoice,
    OptionGroup,
)
from app.models.order import Order, OrderItem, OrderItemOption
from app.models.user import RefreshToken, User

__all__ = [
    "Base",
    "User",
    "RefreshToken",
    "Category",
    "DietaryTag",
    "Allergen",
    "MenuItem",
    "OptionGroup",
    "OptionChoice",
    "Cart",
    "CartItem",
    "CartItemOption",
    "Order",
    "OrderItem",
    "OrderItemOption",
    "Conversation",
    "Message",
    "AuditLog",
]
