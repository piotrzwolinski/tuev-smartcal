"""Tests for the FastAPI endpoints."""

import pytest
from httpx import AsyncClient, ASGITransport
from main import app
from load_graph import load_schema


@pytest.fixture(scope="module", autouse=True)
def load_graph():
    load_schema(clear_first=True)


@pytest.mark.asyncio
async def test_health():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["graph"]["nodes"] >= 100


@pytest.mark.asyncio
async def test_graph_load_endpoint():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post("/api/graph/load")
    assert resp.status_code == 200
    data = resp.json()
    assert data["node_count"] >= 100


@pytest.mark.asyncio
async def test_calculate_returns_sse():
    """POST /api/calculate returns an SSE stream."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/api/calculate",
            json={
                "input": "Bürogebäude, 5000m² BGF",
                "params": {"gebaeudetyp": "Bürogebäude", "bgf_m2": 5000},
            },
            timeout=60,
        )
    assert resp.status_code == 200
    assert "text/event-stream" in resp.headers.get("content-type", "")
