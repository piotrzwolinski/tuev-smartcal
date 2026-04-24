"""Tests for graph loading and schema integrity."""

import pytest
from database import get_graph, query
from load_graph import load_schema


@pytest.fixture(scope="module")
def loaded_graph():
    """Load graph once for all tests in this module."""
    stats = load_schema(clear_first=True)
    assert not stats["errors"], f"Schema load errors: {stats['errors'][:3]}"
    return stats


@pytest.mark.asyncio
async def test_graph_loaded(loaded_graph):
    """After loading, node count >= 120 and edge count >= 200."""
    assert loaded_graph["node_count"] >= 120, f"Only {loaded_graph['node_count']} nodes"
    assert loaded_graph["edge_count"] >= 200, f"Only {loaded_graph['edge_count']} edges"


@pytest.mark.asyncio
async def test_node_labels(loaded_graph):
    """All expected labels exist in the graph."""
    result = await query(
        "MATCH (n) WITH labels(n)[0] AS label RETURN DISTINCT label"
    )
    labels = {r["label"] for r in result}
    expected = {
        "Dienstleistung", "Preisposition", "Merkmal", "Gebaeudetyp",
        "Stressor", "Trait",
    }
    missing = expected - labels
    assert not missing, f"Missing labels: {missing}"


@pytest.mark.asyncio
async def test_sample_service(loaded_graph):
    """DGUV V3 ortsveränderlich service exists with expected properties."""
    result = await query(
        "MATCH (d:Dienstleistung {id: 'DL_DGUV_ORTV'}) RETURN properties(d) AS props"
    )
    assert len(result) == 1
    props = result[0]["props"]
    assert "name" in props


@pytest.mark.asyncio
async def test_schaetzt_edges(loaded_graph):
    """BGF Merkmal has SCHAETZT edges (estimation chain)."""
    result = await query(
        "MATCH (m:Merkmal {id: 'MERK_BGF'})-[r:SCHAETZT]->(target) "
        "RETURN count(r) AS cnt"
    )
    assert result[0]["cnt"] >= 3, "BGF should estimate at least 3 quantities"


@pytest.mark.asyncio
async def test_gleiche_begehung(loaded_graph):
    """Bundle relationships exist between services."""
    result = await query(
        "MATCH ()-[r:GLEICHE_BEGEHUNG]->() RETURN count(r) AS cnt"
    )
    assert result[0]["cnt"] >= 5, "Should have at least 5 bundle pairs"


@pytest.mark.asyncio
async def test_stressor_trait_chain(loaded_graph):
    """Stressor/Trait causal chain exists."""
    result = await query(
        "MATCH (s:Stressor)-[r1:EXPOSES_TO]->(t:Trait) RETURN count(r1) AS cnt"
    )
    assert result[0]["cnt"] >= 5, "Should have causal chains"


@pytest.mark.asyncio
async def test_erfordert_pruefung(loaded_graph):
    """Building types have mandatory service relationships."""
    result = await query(
        "MATCH (g:Gebaeudetyp)-[r:ERFORDERT_PRUEFUNG]->(d:Dienstleistung) "
        "RETURN count(r) AS cnt"
    )
    assert result[0]["cnt"] >= 5, "Should have mandatory service links"
