"""Shared-secret API key auth via X-API-Key header.

All requests to `/api/*` require the `X-API-Key: <SMARTCAL_API_KEY>` header.
Key is shared between frontend (Next.js Route Handler) and backend.
Browser never sees the key — injected server-side via proxy.
"""

import hmac
import os

from fastapi import Request
from fastapi.responses import JSONResponse

HEADER_NAME = "x-api-key"

_KEY = os.getenv("SMARTCAL_API_KEY", "").strip()

if not _KEY:
    raise RuntimeError(
        "SMARTCAL_API_KEY is not set. Refusing to start an unauthenticated backend."
    )


async def api_key_middleware(request: Request, call_next):
    provided = request.headers.get(HEADER_NAME, "")
    if not hmac.compare_digest(provided, _KEY):
        return JSONResponse({"detail": "Unauthorized"}, status_code=401)
    return await call_next(request)
