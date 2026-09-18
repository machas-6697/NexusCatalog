"""
app/models/mongo/review.py
─────────────────────────────────────────────────────────────
Pydantic schemas and models for `reviews` in the `nexuscatalog_reviews` database.

Keywords implemented:
- Archetype: Product Feedback & Sentiment Engine
- Technical Primitives: Dynamic Schema Flexibility (Document)
- Multi-Tenant: tenant_id scoped reviews
"""

import uuid
from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field


class ReviewDocument(BaseModel):
    """
    Represents a customer review document stored in MongoDB database `nexuscatalog_reviews`.
    Supports dynamic pros/cons arrays and arbitrary rating attributes.
    """
    id: str = Field(..., alias="_id")
    tenant_id: str
    product_id: str
    user_id: str
    user_email: str
    rating: int = Field(..., ge=1, le=5, description="Score from 1 to 5")
    title: str
    comment: str
    verified_purchase: bool = True
    pros: list[str] = Field(default_factory=list)
    cons: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime

    model_config = {"populate_by_name": True}


class ReviewCreate(BaseModel):
    """Payload accepted when submitting a new review."""
    product_id: str
    rating: int = Field(..., ge=1, le=5)
    title: str
    comment: str
    verified_purchase: bool = True
    pros: list[str] = Field(default_factory=list)
    cons: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class ReviewResponse(BaseModel):
    """API response model for reviews."""
    id: str
    tenant_id: str
    product_id: str
    user_id: str
    user_email: str
    rating: int
    title: str
    comment: str
    verified_purchase: bool
    pros: list[str]
    cons: list[str]
    metadata: dict[str, Any]
    created_at: datetime
