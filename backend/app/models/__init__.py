"""Import all models so SQLAlchemy metadata + Alembic see them."""

from app.models.audit import AuditLog
from app.models.base import Base
from app.models.cart import Cart, CartItem, CartItemOption
from app.models.chat import Conversation, Message
from app.models.feedback import ConversationFeedback
from app.models.knowledge import Document, DocumentChunk
from app.models.menu import (
    Allergen,
    Category,
    DietaryTag,
    MenuItem,
    OptionChoice,
    OptionGroup,
)
from app.models.order import Order, OrderItem, OrderItemOption
from app.models.product_embedding import ProductEmbedding
from app.models.user import RefreshToken, User
from app.models.user_memory import UserPreference

__all__ = [
    "Base",
    "User",
    "RefreshToken",
    "UserPreference",
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
    "Document",
    "DocumentChunk",
    "ProductEmbedding",
    "ConversationFeedback",
]
