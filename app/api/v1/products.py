"""
app/api/v1/products.py
─────────────────────────────────────────────────────────────
Product catalog endpoints — MongoDB-backed with cursor pagination.

GET    /api/v1/products           →  List products (buyer + admin, cursor-paged)
POST   /api/v1/products           →  Create product (admin only)
GET    /api/v1/products/{id}      →  Get product by ID (buyer + admin)
PATCH  /api/v1/products/{id}      →  Update product (admin only)
DELETE /api/v1/products/{id}      →  Delete product (admin only)

Cursor Pagination:
  - Client sends ?limit=20&cursor=<opaque_cursor>
  - Server returns next_cursor in response body
  - next_cursor is base64-encoded last document's _id
  - When next_cursor is null, there are no more pages
"""

import base64
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, Query

from app.core.dependencies import get_current_user, get_tenant_id, require_role
from app.core.exceptions import NotFoundError
from app.db.mongo import get_collection
from app.models.mongo.product import ProductCreate, ProductUpdate, new_product_doc
from app.models.pg.user import User
from app.schemas.product import PaginatedProductResponse, ProductRead

router = APIRouter(prefix="/products", tags=["Products"])

PRODUCTS_COLLECTION = "products"


def _encode_cursor(value: str) -> str:
    """Encodes a MongoDB _id into an opaque base64 cursor string."""
    return base64.urlsafe_b64encode(value.encode()).decode()


def _decode_cursor(cursor: str) -> str:
    """Decodes a base64 cursor string back to a MongoDB _id."""
    try:
        return base64.urlsafe_b64decode(cursor.encode()).decode()
    except Exception:
        from app.core.exceptions import BadRequestError
        raise BadRequestError("Invalid pagination cursor")


def _doc_to_read(doc: dict) -> ProductRead:
    """Converts a raw MongoDB document dict to a ProductRead schema."""
    return ProductRead(
        id=doc["_id"],
        tenant_id=doc["tenant_id"],
        name=doc["name"],
        description=doc["description"],
        price=doc["price"],
        stock=doc["stock"],
        category=doc["category"],
        attributes=doc.get("attributes", {}),
        created_at=doc["created_at"],
        updated_at=doc["updated_at"],
    )


@router.get(
    "",
    response_model=PaginatedProductResponse,
    summary="List products with cursor pagination",
    description=(
        "Returns a paginated list of products for the authenticated user's tenant. "
        "Pass `cursor` from the previous response to fetch the next page."
    ),
)
async def list_products(
    limit: int = Query(default=20, ge=1, le=100, description="Number of products per page"),
    cursor: Optional[str] = Query(default=None, description="Opaque pagination cursor"),
    category: Optional[str] = Query(default=None, description="Filter by category"),
    _: User = Depends(get_current_user),
    tenant_id: str = Depends(get_tenant_id),
) -> PaginatedProductResponse:
    collection = get_collection(PRODUCTS_COLLECTION)

    # ── Build filter ──────────────────────────────────────────
    query_filter: dict = {"tenant_id": tenant_id}
    if category:
        query_filter["category"] = category
    if cursor:
        last_id = _decode_cursor(cursor)
        query_filter["_id"] = {"$gt": last_id}

    # ── Count total (without cursor filter for accurate count) ─
    count_filter: dict = {"tenant_id": tenant_id}
    if category:
        count_filter["category"] = category
    total = await collection.count_documents(count_filter)

    # ── Fetch page ────────────────────────────────────────────
    docs = await collection.find(query_filter).sort("_id", 1).limit(limit + 1).to_list(limit + 1)

    # ── Determine next cursor ─────────────────────────────────
    has_more = len(docs) > limit
    if has_more:
        docs = docs[:limit]

    next_cursor = _encode_cursor(docs[-1]["_id"]) if has_more and docs else None
    items = [_doc_to_read(doc) for doc in docs]

    return PaginatedProductResponse(items=items, total=total, next_cursor=next_cursor)


@router.post(
    "",
    response_model=ProductRead,
    status_code=201,
    summary="Create a product",
    description="Creates a new product in the catalog. Admin or Manager access required.",
)
async def create_product(
    body: ProductCreate,
    _: User = Depends(require_role("admin", "manager")),
    tenant_id: str = Depends(get_tenant_id),
) -> ProductRead:
    collection = get_collection(PRODUCTS_COLLECTION)
    product_id = str(uuid.uuid4())
    doc = new_product_doc(tenant_id, product_id, body)
    await collection.insert_one(doc)
    return _doc_to_read(doc)


@router.get(
    "/{product_id}",
    response_model=ProductRead,
    summary="Get product by ID",
)
async def get_product(
    product_id: str,
    _: User = Depends(get_current_user),
    tenant_id: str = Depends(get_tenant_id),
) -> ProductRead:
    collection = get_collection(PRODUCTS_COLLECTION)
    doc = await collection.find_one({"_id": product_id, "tenant_id": tenant_id})
    if doc is None:
        raise NotFoundError("Product")
    return _doc_to_read(doc)


@router.patch(
    "/{product_id}",
    response_model=ProductRead,
    summary="Update a product",
    description="Partially update product fields. Admin or Manager access required.",
)
async def update_product(
    product_id: str,
    body: ProductUpdate,
    _: User = Depends(require_role("admin", "manager")),
    tenant_id: str = Depends(get_tenant_id),
) -> ProductRead:
    collection = get_collection(PRODUCTS_COLLECTION)

    # ── Build update dict (only non-None fields) ──────────────
    update_data = body.model_dump(exclude_none=True)
    if not update_data:
        from app.core.exceptions import BadRequestError
        raise BadRequestError("No fields provided for update")

    update_data["updated_at"] = datetime.now(timezone.utc)

    result = await collection.find_one_and_update(
        {"_id": product_id, "tenant_id": tenant_id},
        {"$set": update_data},
        return_document=True,
    )
    if result is None:
        raise NotFoundError("Product")
    return _doc_to_read(result)


@router.delete(
    "/{product_id}",
    status_code=204,
    summary="Delete a product",
    description="Removes a product from the catalog. Admin access required.",
)
async def delete_product(
    product_id: str,
    _: User = Depends(require_role("admin")),
    tenant_id: str = Depends(get_tenant_id),
) -> None:
    collection = get_collection(PRODUCTS_COLLECTION)
    result = await collection.delete_one({"_id": product_id, "tenant_id": tenant_id})
    if result.deleted_count == 0:
        raise NotFoundError("Product")
