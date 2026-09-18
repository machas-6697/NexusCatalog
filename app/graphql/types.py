"""
app/graphql/types.py
─────────────────────────────────────────────────────────────
Strawberry GraphQL type definitions.

These are the GraphQL-layer types that the Playground exposes.
They mirror the Pydantic schemas but use Strawberry decorators
so they appear correctly in the schema introspection.
"""

from datetime import datetime
from typing import Any, Optional

import strawberry


@strawberry.type
class ProductType:
    """GraphQL type representing a single product from MongoDB."""
    id: str
    tenant_id: str
    name: str
    description: str
    price: float
    stock: int
    category: str
    created_at: datetime
    updated_at: datetime


@strawberry.type
class ProductPageType:
    """
    Paginated product response — mirrors REST PaginatedProductResponse
    but in GraphQL shape.
    """
    items: list[ProductType]
    total: int
    next_cursor: Optional[str]


@strawberry.input
class ProductInput:
    """Input type for creating a new product via GraphQL mutation."""
    name: str
    description: str
    price: float
    stock: int = 0
    category: str


@strawberry.input
class ProductFilterInput:
    """Optional filters for product queries."""
    category: Optional[str] = None
    limit: int = 20
    cursor: Optional[str] = None


@strawberry.type
class ReviewType:
    """GraphQL type representing a customer review from MongoDB."""
    id: str
    tenant_id: str
    product_id: str
    user_id: str
    user_email: str
    rating: int
    title: str
    comment: str
    verified_purchase: bool
    created_at: datetime


@strawberry.input
class ReviewInput:
    """Input type for submitting a review via GraphQL."""
    product_id: str
    rating: int
    title: str
    comment: str
    verified_purchase: bool = True
