"""
app/api/v1/events.py
─────────────────────────────────────────────────────────────
Clickstream & Telemetry Analytics endpoints.
Reads/writes MongoDB database: `nexuscatalog_events`.

Roles:
- Any authenticated user can record telemetry events.
- `admin` and `auditor` can query analytical event logs.
- `manager` and `buyer` cannot view global analytics events (403 Forbidden).

Keywords implemented:
- Archetype: Clickstream & Telemetry Analytics Engine
- Technical Primitives: Dynamic Schema Flexibility (Document)
- Stack & Telemetry: User telemetry and analytical tracking
"""

import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel

from app.core.dependencies import get_current_user, get_tenant_id, require_role
from app.db.mongo import get_events_collection
from app.models.mongo.event import EventCreate, EventDocument, EventResponse
from app.models.pg.user import User

router = APIRouter(prefix="/events", tags=["Events & Analytics"])


@router.post(
    "",
    response_model=EventResponse,
    status_code=201,
    summary="Record telemetry event",
    description="Ingests user telemetry, page views, or clickstream events.",
)
async def record_event(
    body: EventCreate,
    request: Request,
    current_user: User = Depends(require_role("admin", "manager", "buyer")),
    tenant_id: str = Depends(get_tenant_id),
) -> EventResponse:
    collection = get_events_collection()
    event_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    client_ip = request.client.host if request.client else "127.0.0.1"

    doc = {
        "_id": event_id,
        "tenant_id": tenant_id,
        "session_id": body.session_id,
        "user_id": current_user.id,
        "event_type": body.event_type,
        "resource_id": body.resource_id,
        "properties": body.properties,
        "ip_address": client_ip,
        "timestamp": now,
    }
    await collection.insert_one(doc)

    return EventResponse(
        id=event_id,
        tenant_id=tenant_id,
        session_id=body.session_id,
        user_id=current_user.id,
        event_type=body.event_type,
        resource_id=body.resource_id,
        properties=body.properties,
        ip_address=client_ip,
        timestamp=now,
    )


@router.get(
    "",
    response_model=list[EventResponse],
    summary="List telemetry events",
    description="Returns telemetry and event logs. Permitted for admin and auditor.",
)
async def list_events(
    event_type: str | None = None,
    limit: int = Query(default=50, ge=1, le=200),
    current_user: User = Depends(require_role("admin", "manager", "auditor")),
    tenant_id: str = Depends(get_tenant_id),
) -> list[EventResponse]:
    collection = get_events_collection()

    filter_query: dict[str, Any] = {"tenant_id": tenant_id}
    if event_type:
        filter_query["event_type"] = event_type

    cursor = collection.find(filter_query).sort("timestamp", -1).limit(limit)
    docs = await cursor.to_list(length=limit)

    return [
        EventResponse(
            id=d["_id"],
            tenant_id=d["tenant_id"],
            session_id=d["session_id"],
            user_id=d.get("user_id"),
            event_type=d["event_type"],
            resource_id=d.get("resource_id"),
            properties=d.get("properties", {}),
            ip_address=d.get("ip_address"),
            timestamp=d["timestamp"],
        )
        for d in docs
    ]
