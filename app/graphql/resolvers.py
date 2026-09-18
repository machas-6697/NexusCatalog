"""
app/graphql/resolvers.py
─────────────────────────────────────────────────────────────
GraphQL resolver functions — query and mutation logic.

Auth for GraphQL:
  The AuthMiddleware already validated the JWT and set
  request.state.token_data for all requests (including /graphql).
  Resolvers extract the tenant_id from info.context["request"].state.
  If the state is missing, they raise PermissionError → 401.

All resolvers are tenant-scoped: they only touch documents
where tenant_id matches the authenticated user's tenant.
"""

import base64
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from strawberry.types import Info

from app.core.exceptions import ForbiddenError, NotFoundError, UnauthorizedError
from app.db.mongo import get_collection
from app.graphql.types import ProductFilterInput, ProductInput, ProductPageType, ProductType

PRODUCTS_COLLECTION = "products"


# ── Helpers ───────────────────────────────────────────────────

def _get_tenant_and_role(info: Info) -> tuple[str, str]:
    """
    Extracts tenant_id and role from the request state injected by AuthMiddleware.
    Raises UnauthorizedError if the state is not populated.
    """
    request = info.context["request"]
    token_data = getattr(request.state, "token_data", None)
    if token_data is None:
        raise UnauthorizedError("Authentication required for GraphQL operations")
    return token_data["tenant_id"], token_data["role"]


def _doc_to_type(doc: dict) -> ProductType:
    return ProductType(
        id=doc["_id"],
        tenant_id=doc["tenant_id"],
        name=doc["name"],
        description=doc["description"],
        price=doc["price"],
        stock=doc["stock"],
        category=doc["category"],
        created_at=doc["created_at"],
        updated_at=doc["updated_at"],
    )


def _encode_cursor(value: str) -> str:
    return base64.urlsafe_b64encode(value.encode()).decode()


def _decode_cursor(cursor: str) -> str:
    try:
        return base64.urlsafe_b64decode(cursor.encode()).decode()
    except Exception:
        from app.core.exceptions import BadRequestError
        raise BadRequestError("Invalid pagination cursor")


# ── Query Resolvers ───────────────────────────────────────────

async def resolve_products(
    info: Info,
    filters: Optional[ProductFilterInput] = None,
) -> ProductPageType:
    """
    Query: products(filters: ProductFilterInput) -> ProductPageType

    Returns a paginated list of products for the authenticated tenant.
    Buyers and admins can both run this query.
    """
    tenant_id, _ = _get_tenant_and_role(info)
    collection = get_collection(PRODUCTS_COLLECTION)

    limit = filters.limit if filters else 20
    cursor = filters.cursor if filters else None
    category = filters.category if filters else None

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
    return ProductPageType(
        items=[_doc_to_type(d) for d in docs],
        total=total,
        next_cursor=next_cursor,
    )


async def resolve_product(info: Info, product_id: str) -> ProductType:
    """
    Query: product(productId: String!) -> ProductType

    Returns a single product by ID, scoped to the tenant.
    """
    tenant_id, _ = _get_tenant_and_role(info)
    collection = get_collection(PRODUCTS_COLLECTION)
    doc = await collection.find_one({"_id": product_id, "tenant_id": tenant_id})
    if doc is None:
        raise NotFoundError("Product")
    return _doc_to_type(doc)


# ── Mutation Resolvers ────────────────────────────────────────

async def resolve_create_product(info: Info, input: ProductInput) -> ProductType:
    """
    Mutation: createProduct(input: ProductInput!) -> ProductType
    Creates a new product. Admin or Manager role required.
    """
    tenant_id, role = _get_tenant_and_role(info)
    if role not in ("admin", "manager"):
        raise ForbiddenError("Only admins and managers can create products via GraphQL")

    collection = get_collection(PRODUCTS_COLLECTION)
    now = datetime.now(timezone.utc)
    product_id = str(uuid.uuid4())
    doc = {
        "_id": product_id,
        "tenant_id": tenant_id,
        "name": input.name,
        "description": input.description,
        "price": input.price,
        "stock": input.stock,
        "category": input.category,
        "attributes": {},
        "created_at": now,
        "updated_at": now,
    }
    await collection.insert_one(doc)
    return _doc_to_type(doc)


async def resolve_delete_product(info: Info, product_id: str) -> bool:
    """
    Mutation: deleteProduct(productId: String!) -> Boolean
    Deletes a product. Admin role required.
    """
    tenant_id, role = _get_tenant_and_role(info)
    if role != "admin":
        raise ForbiddenError("Only admins can delete products via GraphQL")

    collection = get_collection(PRODUCTS_COLLECTION)
    result = await collection.delete_one({"_id": product_id, "tenant_id": tenant_id})
    if result.deleted_count == 0:
        raise NotFoundError("Product")
    return True


# ── Review Resolvers ──────────────────────────────────────────

async def resolve_reviews(info: Info, product_id: Optional[str] = None) -> list:
    """Query: reviews(productId: String) -> [ReviewType]"""
    from app.db.mongo import get_reviews_collection
    from app.graphql.types import ReviewType

    tenant_id, _ = _get_tenant_and_role(info)
    collection = get_reviews_collection()

    filter_q = {"tenant_id": tenant_id}
    if product_id:
        filter_q["product_id"] = product_id

    cursor = collection.find(filter_q).sort("created_at", -1).limit(50)
    docs = await cursor.to_list(length=50)

    return [
        ReviewType(
            id=d["_id"],
            tenant_id=d["tenant_id"],
            product_id=d["product_id"],
            user_id=d.get("user_id", ""),
            user_email=d.get("user_email", ""),
            rating=d["rating"],
            title=d["title"],
            comment=d["comment"],
            verified_purchase=d.get("verified_purchase", True),
            created_at=d["created_at"],
        )
        for d in docs
    ]


async def resolve_create_review(info: Info, input: Any) -> Any:
    """Mutation: createReview(input: ReviewInput!) -> ReviewType"""
    from app.db.mongo import get_reviews_collection
    from app.graphql.types import ReviewType

    tenant_id, role = _get_tenant_and_role(info)
    if role == "auditor":
        raise ForbiddenError("Auditors have read-only permissions and cannot submit reviews")

    request = info.context["request"]
    token_data = getattr(request.state, "token_data", {})
    user_id = token_data.get("sub", "")
    user_email = token_data.get("email", "")

    collection = get_reviews_collection()
    review_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)

    doc = {
        "_id": review_id,
        "tenant_id": tenant_id,
        "product_id": input.product_id,
        "user_id": user_id,
        "user_email": user_email,
        "rating": input.rating,
        "title": input.title,
        "comment": input.comment,
        "verified_purchase": input.verified_purchase,
        "created_at": now,
    }
    await collection.insert_one(doc)

    return ReviewType(
        id=review_id,
        tenant_id=tenant_id,
        product_id=input.product_id,
        user_id=user_id,
        user_email=user_email,
        rating=input.rating,
        title=input.title,
        comment=input.comment,
        verified_purchase=input.verified_purchase,
        created_at=now,
    )
