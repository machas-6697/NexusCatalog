"""
app/graphql/schema.py
─────────────────────────────────────────────────────────────
Strawberry GraphQL schema — assembles Query + Mutation types
and exports the `graphql_app` ASGI app that FastAPI mounts.
"""

import strawberry
from strawberry.fastapi import GraphQLRouter
from strawberry.types import Info
from typing import Optional

from app.graphql.types import (
    ProductFilterInput,
    ProductInput,
    ProductPageType,
    ProductType,
    ReviewInput,
    ReviewType,
)
from app.graphql.resolvers import (
    resolve_create_product,
    resolve_create_review,
    resolve_delete_product,
    resolve_product,
    resolve_products,
    resolve_reviews,
)


# ── Query root ────────────────────────────────────────────────

@strawberry.type
class Query:
    @strawberry.field(description="List products with optional cursor-based pagination and filtering.")
    async def products(
        self,
        info: Info,
        filters: Optional[ProductFilterInput] = None,
    ) -> ProductPageType:
        return await resolve_products(info, filters)

    @strawberry.field(description="Get a single product by its ID.")
    async def product(self, info: Info, product_id: str) -> ProductType:
        return await resolve_product(info, product_id)

    @strawberry.field(description="List customer reviews for products.")
    async def reviews(
        self,
        info: Info,
        product_id: Optional[str] = None,
    ) -> list[ReviewType]:
        return await resolve_reviews(info, product_id)


# ── Mutation root ─────────────────────────────────────────────

@strawberry.type
class Mutation:
    @strawberry.mutation(description="Create a new product. Requires admin or manager role.")
    async def create_product(self, info: Info, input: ProductInput) -> ProductType:
        return await resolve_create_product(info, input)

    @strawberry.mutation(description="Delete a product by ID. Requires admin role.")
    async def delete_product(self, info: Info, product_id: str) -> bool:
        return await resolve_delete_product(info, product_id)

    @strawberry.mutation(description="Submit customer review. Permitted for buyer, manager, admin.")
    async def create_review(self, info: Info, input: ReviewInput) -> ReviewType:
        return await resolve_create_review(info, input)


# ── Schema + ASGI app ─────────────────────────────────────────

schema = strawberry.Schema(query=Query, mutation=Mutation)

# GraphQLRouter mounts at /graphql and includes the Playground UI
graphql_app = GraphQLRouter(
    schema,
    graphql_ide="graphiql",   # Enables the interactive GraphQL Playground
)
