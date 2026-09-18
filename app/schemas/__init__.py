"""
Pydantic request/response schemas for REST API endpoints.
"""

from app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse
from app.schemas.order import OrderCreate, OrderItemCreate, OrderRead, OrderStatusUpdate
from app.schemas.product import (
    PaginatedProductResponse,
    PaginatedProductResponseV2,
    ProductRead,
    ProductReadV2,
)
from app.schemas.tenant import TenantCreate, TenantRead, TenantUpdate
from app.schemas.user import UserRead, UserUpdate

__all__ = [
    "LoginRequest",
    "OrderCreate",
    "OrderItemCreate",
    "OrderRead",
    "OrderStatusUpdate",
    "PaginatedProductResponse",
    "PaginatedProductResponseV2",
    "ProductRead",
    "ProductReadV2",
    "RegisterRequest",
    "TenantCreate",
    "TenantRead",
    "TenantUpdate",
    "TokenResponse",
    "UserRead",
    "UserUpdate",
]
