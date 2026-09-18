"""
Strawberry GraphQL interface — products and reviews over the same polyglot data layer.
"""

from app.graphql.schema import graphql_app, schema

__all__ = ["graphql_app", "schema"]
