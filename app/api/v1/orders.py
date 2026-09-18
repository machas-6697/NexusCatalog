"""
app/api/v1/orders.py
─────────────────────────────────────────────────────────────
Order management endpoints — PostgreSQL ACID transactions.

POST  /api/v1/orders          →  Place a new order (buyer + admin)
GET   /api/v1/orders          →  List ALL orders for tenant (admin only)
GET   /api/v1/orders/mine     →  List MY orders (buyer + admin)
GET   /api/v1/orders/{id}     →  Get order by ID
PATCH /api/v1/orders/{id}     →  Update order status (admin only)

ACID Guarantee:
  The entire order creation (Order row + N OrderItem rows + total
  calculation) executes inside a single SQLAlchemy async session
  that auto-commits on success or rolls back on any failure.
"""

import uuid
from decimal import Decimal

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.dependencies import get_current_user, get_tenant_id, require_role
from app.core.exceptions import NotFoundError
from app.db.postgres import get_db
from app.models.pg.order import Order, OrderItem
from app.models.pg.user import User
from app.schemas.order import OrderCreate, OrderRead, OrderStatusUpdate

router = APIRouter(prefix="/orders", tags=["Orders"])


@router.post(
    "",
    response_model=OrderRead,
    status_code=201,
    summary="Place a new order",
    description="Creates an order with one or more line items inside an ACID transaction.",
)
async def create_order(
    body: OrderCreate,
    current_user: User = Depends(require_role("admin", "manager", "buyer")),
    tenant_id: str = Depends(get_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> OrderRead:
    if not body.items:
        from app.core.exceptions import BadRequestError
        raise BadRequestError("Order must contain at least one item")

    # ── Calculate total ───────────────────────────────────────
    total = sum(
        Decimal(str(item.unit_price)) * item.quantity
        for item in body.items
    )

    # ── Create Order ──────────────────────────────────────────
    order = Order(
        id=str(uuid.uuid4()),
        tenant_id=tenant_id,
        user_id=current_user.id,
        total_amount=total,
    )
    for item in body.items:
        order.items.append(
            OrderItem(
                id=str(uuid.uuid4()),
                product_id=item.product_id,
                product_name=item.product_name,
                quantity=item.quantity,
                unit_price=item.unit_price,
            )
        )
    db.add(order)
    await db.commit()
    await db.refresh(order, attribute_names=["items"])
    return OrderRead.model_validate(order)


@router.get(
    "",
    response_model=list[OrderRead],
    summary="List all tenant orders",
    description="Returns all orders for the authenticated user's tenant. Admin, Manager, and Auditor access permitted.",
)
async def list_all_orders(
    _: User = Depends(require_role("admin", "manager", "auditor")),
    tenant_id: str = Depends(get_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> list[OrderRead]:
    result = await db.execute(
        select(Order)
        .where(Order.tenant_id == tenant_id)
        .options(selectinload(Order.items))
        .order_by(Order.created_at.desc())
    )
    orders = result.scalars().all()
    return [OrderRead.model_validate(o) for o in orders]


@router.get(
    "/mine",
    response_model=list[OrderRead],
    summary="List my orders",
    description="Returns orders placed by the currently authenticated user.",
)
async def list_my_orders(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[OrderRead]:
    result = await db.execute(
        select(Order)
        .where(Order.user_id == current_user.id)
        .options(selectinload(Order.items))
        .order_by(Order.created_at.desc())
    )
    orders = result.scalars().all()
    return [OrderRead.model_validate(o) for o in orders]


@router.get(
    "/{order_id}",
    response_model=OrderRead,
    summary="Get order by ID",
)
async def get_order(
    order_id: str,
    current_user: User = Depends(get_current_user),
    tenant_id: str = Depends(get_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> OrderRead:
    result = await db.execute(
        select(Order)
        .where(Order.id == order_id, Order.tenant_id == tenant_id)
        .options(selectinload(Order.items))
    )
    order = result.scalar_one_or_none()
    if order is None:
        raise NotFoundError("Order")

    # Buyers can only see their own orders
    if current_user.role == "buyer" and order.user_id != current_user.id:
        from app.core.exceptions import ForbiddenError
        raise ForbiddenError("You can only view your own orders")

    return OrderRead.model_validate(order)


@router.patch(
    "/{order_id}",
    response_model=OrderRead,
    summary="Update order status",
    description="Updates the status of an order. Admin and Manager access permitted.",
)
async def update_order_status(
    order_id: str,
    body: OrderStatusUpdate,
    _: User = Depends(require_role("admin", "manager")),
    tenant_id: str = Depends(get_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> OrderRead:
    valid_statuses = {"pending", "confirmed", "shipped", "delivered", "cancelled"}
    if body.status not in valid_statuses:
        from app.core.exceptions import BadRequestError
        raise BadRequestError(f"Invalid status. Must be one of: {valid_statuses}")

    result = await db.execute(
        select(Order)
        .where(Order.id == order_id, Order.tenant_id == tenant_id)
        .options(selectinload(Order.items))
    )
    order = result.scalar_one_or_none()
    if order is None:
        raise NotFoundError("Order")

    order.status = body.status
    db.add(order)
    await db.commit()
    await db.refresh(order, attribute_names=["items"])
    return OrderRead.model_validate(order)
