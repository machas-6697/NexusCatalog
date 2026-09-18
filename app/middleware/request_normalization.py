"""
app/middleware/request_normalization.py
─────────────────────────────────────────────────────────────
ASGI Middleware implementing Request Normalization & Middleware Routing.

Keywords implemented:
- Core Mechanics: Request Normalization
- Technical Primitives: Middleware Routing
- Stack & Telemetry: Distributed Tracing via X-Request-ID and timing
"""

import time
import uuid
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response


class RequestNormalizationMiddleware(BaseHTTPMiddleware):
    """
    Normalizes every incoming HTTP request entering the ASGI pipeline:
    1. Extracts or generates an X-Request-ID correlation token for distributed tracing.
    2. Measures request duration and attaches X-Response-Time-Ms to the response.
    3. Injects security baseline headers (nosniff, frame protection).
    4. Populates request.state.request_id for downstream route handlers and loggers.
    """

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        # 1. Normalization: Ensure request ID exists
        request_id = request.headers.get("X-Request-ID")
        if not request_id or not request_id.strip():
            request_id = str(uuid.uuid4())

        request.state.request_id = request_id
        start_time = time.perf_counter()

        # 2. Process request through downstream pipeline
        response = await call_next(request)

        # 3. Compute execution latency
        process_time_ms = (time.perf_counter() - start_time) * 1000

        # 4. Attach standard tracing & normalization response headers
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Response-Time-Ms"] = f"{process_time_ms:.2f}"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"

        return response
