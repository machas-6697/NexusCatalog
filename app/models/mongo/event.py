"""
app/models/mongo/event.py
─────────────────────────────────────────────────────────────
Pydantic schemas and models for `events` in the `nexuscatalog_events` database.

Keywords implemented:
- Archetype: Clickstream & Telemetry Analytics Engine
- Technical Primitives: Dynamic Schema Flexibility (Document)
- Stack & Telemetry: User telemetry and analytical tracking
"""

from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field


class EventDocument(BaseModel):
    """
    Represents a telemetry / clickstream event in `nexuscatalog_events`.
    Stores dynamic unstructured session details, user-agents, and event payloads.
    """
    id: str = Field(..., alias="_id")
    tenant_id: str
    session_id: str
    user_id: str | None = None
    event_type: str = Field(
        ...,
        description="Type of event: e.g. page_view, product_viewed, cart_add, checkout_start"
    )
    resource_id: str | None = None
    properties: dict[str, Any] = Field(default_factory=dict)
    ip_address: str | None = None
    timestamp: datetime

    model_config = {"populate_by_name": True}


class EventCreate(BaseModel):
    """Payload accepted when sending a client or backend telemetry event."""
    session_id: str
    event_type: str
    resource_id: str | None = None
    properties: dict[str, Any] = Field(default_factory=dict)


class EventResponse(BaseModel):
    """API response model for events."""
    id: str
    tenant_id: str
    session_id: str
    user_id: str | None
    event_type: str
    resource_id: str | None
    properties: dict[str, Any]
    ip_address: str | None
    timestamp: datetime
