"""
app/api/v1/reviews.py
─────────────────────────────────────────────────────────────
Product Reviews & Customer Sentiment endpoints.
Reads/writes MongoDB database: `nexuscatalog_reviews`.

Roles:
- `buyer`, `admin`, `manager`: Can submit reviews
- `auditor`: Strictly read-only (403 Forbidden on POST)
- All roles: Can read reviews

Keywords implemented:
- Archetype: Product Feedback & Sentiment Engine
- Technical Primitives: Dynamic Schema Flexibility (Document)
- Core Mechanics: Cursor-Based Pagination
"""

import base64
import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from app.core.dependencies import get_current_user, get_tenant_id, require_role
from app.core.exceptions import BadRequestError, NotFoundError
from app.db.mongo import get_reviews_collection
from app.models.mongo.review import ReviewCreate, ReviewDocument, ReviewResponse
from app.models.pg.user import User

router = APIRouter(prefix="/reviews", tags=["Reviews"])


def _encode_cursor(value: str) -> str:
    return base64.urlsafe_b64encode(value.encode()).decode()


def _decode_cursor(cursor: str) -> str:
    try:
        return base64.urlsafe_b64decode(cursor.encode()).decode()
    except Exception:
        raise BadRequestError("Invalid pagination cursor")


class PaginatedReviewsResponse(BaseModel):
    items: list[ReviewResponse]
    total: int
    next_cursor: str | None


@router.get(
    "",
    response_model=PaginatedReviewsResponse,
    summary="List product reviews",
    description="Returns reviews for tenant products with cursor-based pagination.",
)
async def list_reviews(
    product_id: str | None = None,
    limit: int = Query(default=10, ge=1, le=50),
    cursor: str | None = Query(default=None),
    current_user: User = Depends(get_current_user),
    tenant_id: str = Depends(get_tenant_id),
) -> PaginatedReviewsResponse:
    collection = get_reviews_collection()

    filter_query: dict[str, Any] = {"tenant_id": tenant_id}
    if product_id:
        filter_query["product_id"] = product_id

    if cursor:
        last_id = _decode_cursor(cursor)
        filter_query["_id"] = {"$gt": last_id}

    total = await collection.count_documents({"tenant_id": tenant_id})
    cursor_obj = collection.find(filter_query).sort("_id", 1).limit(limit + 1)
    docs = await cursor_obj.to_list(length=limit + 1)

    next_cursor = None
    if len(docs) > limit:
        docs = docs[:limit]
        next_cursor = _encode_cursor(docs[-1]["_id"])

    items = [
        ReviewResponse(
            id=d["_id"],
            tenant_id=d["tenant_id"],
            product_id=d["product_id"],
            user_id=d["user_id"],
            user_email=d["user_email"],
            rating=d["rating"],
            title=d["title"],
            comment=d["comment"],
            verified_purchase=d.get("verified_purchase", True),
            pros=d.get("pros", []),
            cons=d.get("cons", []),
            metadata=d.get("metadata", {}),
            created_at=d["created_at"],
        )
        for d in docs
    ]
    return PaginatedReviewsResponse(items=items, total=total, next_cursor=next_cursor)


@router.post(
    "",
    response_model=ReviewResponse,
    status_code=201,
    summary="Submit a product review",
    description="Submits customer feedback. Permitted for buyer, admin, manager (Auditor is read-only).",
)
async def create_review(
    body: ReviewCreate,
    current_user: User = Depends(require_role("buyer", "admin", "manager")),
    tenant_id: str = Depends(get_tenant_id),
) -> ReviewResponse:
    collection = get_reviews_collection()
    review_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)

    doc = {
        "_id": review_id,
        "tenant_id": tenant_id,
        "product_id": body.product_id,
        "user_id": current_user.id,
        "user_email": current_user.email,
        "rating": body.rating,
        "title": body.title,
        "comment": body.comment,
        "verified_purchase": body.verified_purchase,
        "pros": body.pros,
        "cons": body.cons,
        "metadata": body.metadata,
        "created_at": now,
    }

    await collection.insert_one(doc)

    return ReviewResponse(
        id=review_id,
        tenant_id=tenant_id,
        product_id=body.product_id,
        user_id=current_user.id,
        user_email=current_user.email,
        rating=body.rating,
        title=body.title,
        comment=body.comment,
        verified_purchase=body.verified_purchase,
        pros=body.pros,
        cons=body.cons,
        metadata=body.metadata,
        created_at=now,
    )
