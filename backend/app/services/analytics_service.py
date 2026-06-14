"""Manager analytics: inventory, profit/margin, and AI-attributed sales.

All money is integer cents. "Sales" = orders not in pending_payment/cancelled.
Profit uses MenuItem.cost_cents (modelled COGS). Attribution uses Order.source /
Order.conversation_id, set when a chat tool drove items into the cart.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.menu import Category, MenuItem
from app.models.order import Order, OrderItem

LOW_STOCK_THRESHOLD = 15
_SALE_STATUSES = ("placed", "preparing", "ready", "completed")


def _since(days: int) -> datetime:
    return datetime.now(tz=timezone.utc) - timedelta(days=max(1, days))


def inventory_summary(db: Session) -> dict:
    total = db.execute(select(func.count()).select_from(MenuItem)).scalar() or 0
    out_of_stock = db.execute(
        select(func.count()).select_from(MenuItem).where(
            (MenuItem.is_available.is_(False)) | (MenuItem.stock_qty <= 0)
        )
    ).scalar() or 0
    low_stock_count = db.execute(
        select(func.count()).select_from(MenuItem).where(
            MenuItem.is_available.is_(True),
            MenuItem.stock_qty > 0,
            MenuItem.stock_qty <= LOW_STOCK_THRESHOLD,
        )
    ).scalar() or 0

    value_cost, value_retail = db.execute(
        select(
            func.coalesce(func.sum(MenuItem.stock_qty * func.coalesce(MenuItem.cost_cents, 0)), 0),
            func.coalesce(func.sum(MenuItem.stock_qty * MenuItem.price_cents), 0),
        )
    ).one()

    low_rows = db.execute(
        select(MenuItem, Category.slug)
        .join(Category, Category.id == MenuItem.category_id)
        .where(
            MenuItem.is_available.is_(True),
            MenuItem.stock_qty > 0,
            MenuItem.stock_qty <= LOW_STOCK_THRESHOLD,
        )
        .order_by(MenuItem.stock_qty)
        .limit(25)
    ).all()

    by_cat = db.execute(
        select(Category.slug, func.count(MenuItem.id), func.coalesce(func.sum(MenuItem.stock_qty), 0))
        .join(MenuItem, MenuItem.category_id == Category.id)
        .group_by(Category.slug)
        .order_by(Category.slug)
    ).all()

    return {
        "total_products": total,
        "in_stock": total - out_of_stock,
        "out_of_stock": out_of_stock,
        "low_stock_count": low_stock_count,
        "low_stock_threshold": LOW_STOCK_THRESHOLD,
        "inventory_value_cost_cents": int(value_cost),
        "inventory_value_retail_cents": int(value_retail),
        "low_stock": [
            {"sku": mi.sku, "name": mi.name, "category": slug, "stock_qty": mi.stock_qty}
            for mi, slug in low_rows
        ],
        "by_category": [
            {"category": slug, "products": int(cnt), "units": int(units)}
            for slug, cnt, units in by_cat
        ],
    }


def _margin_query(db: Session, days: int, group_by_category: bool):
    since = _since(days)
    revenue = func.coalesce(func.sum(OrderItem.line_total_cents), 0)
    cogs = func.coalesce(func.sum(OrderItem.quantity * func.coalesce(MenuItem.cost_cents, 0)), 0)
    cols = [revenue, cogs]
    if group_by_category:
        cols = [Category.slug, *cols]
    stmt = (
        select(*cols)
        .select_from(OrderItem)
        .join(Order, Order.id == OrderItem.order_id)
        .join(MenuItem, MenuItem.id == OrderItem.menu_item_id)
        .where(Order.status.in_(_SALE_STATUSES), Order.created_at >= since)
    )
    if group_by_category:
        stmt = stmt.join(Category, Category.id == MenuItem.category_id).group_by(Category.slug)
    return stmt


def _margin_row(revenue: int, cogs: int) -> dict:
    revenue, cogs = int(revenue), int(cogs)
    gross = revenue - cogs
    return {
        "revenue_cents": revenue,
        "cogs_cents": cogs,
        "gross_profit_cents": gross,
        "margin_pct": round(gross / revenue * 100, 1) if revenue else 0.0,
    }


def margin_summary(db: Session, days: int = 30) -> dict:
    total = db.execute(_margin_query(db, days, group_by_category=False)).one()
    by_cat = db.execute(_margin_query(db, days, group_by_category=True)).all()
    order_count = db.execute(
        select(func.count()).select_from(Order).where(
            Order.status.in_(_SALE_STATUSES), Order.created_at >= _since(days)
        )
    ).scalar() or 0
    return {
        "period_days": days,
        "order_count": order_count,
        "overall": _margin_row(total[0], total[1]),
        "by_category": sorted(
            ({"category": slug, **_margin_row(rev, cogs)} for slug, rev, cogs in by_cat),
            key=lambda r: r["gross_profit_cents"],
            reverse=True,
        ),
    }


def ai_attribution(db: Session, days: int = 30) -> dict:
    since = _since(days)
    base = (Order.status.in_(_SALE_STATUSES), Order.created_at >= since)

    total_orders, total_revenue = db.execute(
        select(func.count(Order.id), func.coalesce(func.sum(Order.total_cents), 0)).where(*base)
    ).one()
    chat_orders, chat_revenue = db.execute(
        select(func.count(Order.id), func.coalesce(func.sum(Order.total_cents), 0))
        .where(*base, Order.source == "chat")
    ).one()

    top = db.execute(
        select(
            OrderItem.name_snapshot,
            func.coalesce(func.sum(OrderItem.quantity), 0),
            func.coalesce(func.sum(OrderItem.line_total_cents), 0),
        )
        .join(Order, Order.id == OrderItem.order_id)
        .where(*base, Order.source == "chat")
        .group_by(OrderItem.name_snapshot)
        .order_by(func.sum(OrderItem.line_total_cents).desc())
        .limit(10)
    ).all()

    total_orders, total_revenue = int(total_orders), int(total_revenue)
    chat_orders, chat_revenue = int(chat_orders), int(chat_revenue)
    return {
        "period_days": days,
        "total_orders": total_orders,
        "total_revenue_cents": total_revenue,
        "chat_orders": chat_orders,
        "chat_revenue_cents": chat_revenue,
        "order_share_pct": round(chat_orders / total_orders * 100, 1) if total_orders else 0.0,
        "revenue_share_pct": round(chat_revenue / total_revenue * 100, 1) if total_revenue else 0.0,
        "top_chat_products": [
            {"name": name, "units": int(units), "revenue_cents": int(rev)}
            for name, units, rev in top
        ],
    }
