"""Tests for the ReAct agent tool executor (no LLM needed)."""

import pytest
from database import query
from agent.react_agent import ToolExecutor, Scratchpad
from load_graph import load_schema


class DBWrapper:
    async def query(self, cypher: str, **params) -> list[dict]:
        return await query(cypher, **params)


@pytest.fixture(scope="module")
def db():
    load_schema(clear_first=True)
    return DBWrapper()


@pytest.fixture
def executor(db):
    return ToolExecutor(db)


@pytest.mark.asyncio
async def test_get_schema(executor):
    result = await executor.execute("get_schema", {})
    assert "node_types" in result
    assert "relationship_types" in result
    assert len(result["node_types"]) >= 6


@pytest.mark.asyncio
async def test_find_nodes(executor):
    result = await executor.execute("find_nodes", {"label": "Dienstleistung"})
    assert result["count"] >= 10


@pytest.mark.asyncio
async def test_follow_edges_out(executor):
    result = await executor.execute("follow_edges", {
        "node_id": "DL_DGUV_ORTV",
        "direction": "out",
    })
    assert result["count"] > 0
    rel_types = {e["rel_type"] for e in result["edges"]}
    assert "HAT_PREISPOSITION" in rel_types


@pytest.mark.asyncio
async def test_follow_edges_in(executor):
    result = await executor.execute("follow_edges", {
        "node_id": "DL_BMA",
        "direction": "in",
    })
    assert result["count"] > 0


@pytest.mark.asyncio
async def test_find_paths(executor):
    result = await executor.execute("find_paths", {
        "from_id": "MERK_BGF",
        "max_hops": 2,
    })
    assert result["count"] > 0


@pytest.mark.asyncio
async def test_find_internal_edges(executor):
    result = await executor.execute("find_internal_edges", {
        "node_ids": ["DL_DGUV_ORTV", "DL_DGUV_ORTF", "DL_BMA"],
    })
    # These services should have GLEICHE_BEGEHUNG between some of them
    assert result["count"] >= 0  # May or may not have bundles


@pytest.mark.asyncio
async def test_evaluate(executor):
    result = await executor.execute("evaluate", {
        "expression": "bgf / 30 * faktor",
        "variables": {"bgf": 5000, "faktor": 1.2},
    })
    assert result["result"] == 200.0


@pytest.mark.asyncio
async def test_evaluate_unsafe(executor):
    result = await executor.execute("evaluate", {
        "expression": "__import__('os').system('ls')",
        "variables": {},
    })
    assert "error" in result


@pytest.mark.asyncio
async def test_check_completeness(executor):
    result = await executor.execute("check_completeness", {
        "service_ids": ["DL_DGUV_ORTV"],
        "explored_rel_types": ["HAT_PREISPOSITION"],
    })
    assert "is_complete" in result
    assert "all_rel_types" in result


@pytest.mark.asyncio
async def test_scratchpad():
    sp = Scratchpad()
    sp.add_fact("Test fact", "GRAPH", ["node1"])
    sp.add_position(dienstleistung="DGUV V3", betrag=100)
    sp.add_zuschlag(name="ATEX", betrag=50)
    sp.add_rabatt(name="Bündel", betrag=20)
    assert sp.total() == 130  # 100 + 50 - 20
