"""
app/api/v2/products.py
─────────────────────────────────────────────────────────────
v2 Product endpoints — evolved schema with backward-compat translation.

The ONLY difference from v1:
  - `price` is returned as a formatted string "99.99" instead of float 99.99
  - Response wrapper uses `items` key (v1 also uses `items`, so this is consistent)

v1 consumers still work because:
  - The internal data in MongoDB is identical
  - v2 translates the price field at the serialization layer only

Routes:
  GET  /api/v2/products       →  Paginated list (price as string)
  GET  /api/v2/products/{id}  →  Single product (price as string)
"""

import base64
from typing import Optional

from fastapi import APIRouter, Depends, Query

from app.core.dependencies import get_current_user, get_tenant_id
from app.core.exceptions import NotFoundError
from app.db.mongo import get_collection
from app.models.pg.user import User
from app.schemas.product import PaginatedProductResponseV2, ProductReadV2

router = APIRouter(prefix="/products", tags=["Products v2"])

PRODUCTS_COLLECTION = "products"


def _decode_cursor(cursor: str) -> str:
    try:
        return base64.urlsafe_b64decode(cursor.encode()).decode()
    except Exception:
        from app.core.exceptions import BadRequestError
        raise BadRequestError("Invalid pagination cursor")


def _encode_cursor(value: str) -> str:
    return base64.urlsafe_b64encode(value.encode()).decode()


def _doc_to_read_v2(doc: dict) -> ProductReadV2:
    """
    Converts a MongoDB document to v2 schema.
    Key change: price float → formatted decimal string.
    """
    return ProductReadV2(
        id=doc["_id"],
        tenant_id=doc["tenant_id"],
        name=doc["name"],
        description=doc["description"],
        price=f"{doc['price']:.2f}",    # ← v1→v2 translation: float to "xx.xx" string
        stock=doc["stock"],
        category=doc["category"],
        attributes=doc.get("attributes", {}),
        created_at=doc["created_at"],
        updated_at=doc["updated_at"],
    )


@router.get(
    "",
    response_model=PaginatedProductResponseV2,
    summary="[v2] List products",
    description=(
        "Returns products with price formatted as a decimal string (e.g. '99.99'). "
        "This is the v2 schema — backward-compatible translation from the same MongoDB data."
    ),
)
async def list_products_v2(
    limit: int = Query(default=20, ge=1, le=100),
    cursor: Optional[str] = Query(default=None),
    category: Optional[str] = Query(default=None),
    _: User = Depends(get_current_user),
    tenant_id: str = Depends(get_tenant_id),
) -> PaginatedProductResponseV2:
    collection = get_collection(PRODUCTS_COLLECTION)

    query_filter: dict = {"tenant_id": tenant_id}
    if category:
        query_filter["category"] = category
    if cursor:
        last_id = _decode_cursor(cursor)
        query_filter["_id"] = {"$gt": last_id}

    count_filter: dict = {"tenant_id": tenant_id}
    if category:
        count_filter["category"] = category
    total = await collection.count_documents(count_filter)

    docs = await collection.find(query_filter).sort("_id", 1).limit(limit + 1).to_list(limit + 1)
    has_more = len(docs) > limit
    if has_more:
        docs = docs[:limit]

    next_cursor = _encode_cursor(docs[-1]["_id"]) if has_more and docs else None
    items = [_doc_to_read_v2(doc) for doc in docs]

    return PaginatedProductResponseV2(items=items, total=total, next_cursor=next_cursor)


@router.get(
    "/{product_id}",
    response_model=ProductReadV2,
    summary="[v2] Get product by ID",
)
async def get_product_v2(
    product_id: str,
    _: User = Depends(get_current_user),
    tenant_id: str = Depends(get_tenant_id),
) -> ProductReadV2:
    collection = get_collection(PRODUCTS_COLLECTION)
    doc = await collection.find_one({"_id": product_id, "tenant_id": tenant_id})
    if doc is None:
        raise NotFoundError("Product")
    return _doc_to_read_v2(doc)
