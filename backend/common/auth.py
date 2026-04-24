"""Shared-secret API key auth via X-API-Key header.

Wszystkie requesty do `/api/*` wymagają headera `X-API-Key: <SMARTCAL_API_KEY>`.
Klucz jest sharowany między frontendem (Next.js Route Handler) a backendem.
Przeglądarka nigdy nie widzi klucza — jest wstrzykiwany server-side w proxy.
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
