"""FalkorDB multi-graph client.

Supports multiple isolated graphs per product:
- smartcal (legacy demo)
- blitzschutz, rlt, dguv_v3 (Phase 1 products)
"""

import os
from typing import Optional

from falkordb import FalkorDB
from dotenv import load_dotenv

load_dotenv()

FALKORDB_HOST = os.getenv("FALKORDB_HOST", "localhost")
FALKORDB_PORT = int(os.getenv("FALKORDB_PORT", 6379))
FALKORDB_PASSWORD = os.getenv("FALKORDB_PASSWORD", None) or None
DEFAULT_GRAPH = os.getenv("FALKORDB_GRAPH", "smartcal")

_db: Optional[FalkorDB] = None
_graphs: dict = {}


def _get_db() -> FalkorDB:
    global _db
    if _db is None:
        _db = FalkorDB(
            host=FALKORDB_HOST,
            port=FALKORDB_PORT,
            password=FALKORDB_PASSWORD,
        )
    return _db


def get_graph(name: Optional[str] = None):
    """Return FalkorDB graph handle. Cached per graph name."""
    global _graphs
    name = name or DEFAULT_GRAPH
    if name not in _graphs:
        _graphs[name] = _get_db().select_graph(name)
    return _graphs[name]


def result_to_dicts(result) -> list[dict]:
    """Convert FalkorDB result set to list of dicts."""
    if not result.result_set:
        return []
    header = result.header
    rows = []
    for row in result.result_set:
        d = {}
        for i, col in enumerate(header):
            col_name = col[1] if isinstance(col, (list, tuple)) else col
            val = row[i]
            if hasattr(val, "properties"):
                d[col_name] = dict(val.properties)
            else:
                d[col_name] = val
        rows.append(d)
    return rows


async def query(cypher: str, graph_name: Optional[str] = None, **params) -> list[dict]:
    """Execute Cypher query on specified graph."""
    graph = get_graph(graph_name)
    try:
        result = graph.query(cypher, params)
        return result_to_dicts(result)
    except Exception as e:
        return [{"error": str(e)}]
