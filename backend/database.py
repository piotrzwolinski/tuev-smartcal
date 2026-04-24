"""FalkorDB connection and query helpers."""

import os
from falkordb import FalkorDB
from dotenv import load_dotenv

load_dotenv()

FALKORDB_HOST = os.getenv("FALKORDB_HOST", "localhost")
FALKORDB_PORT = int(os.getenv("FALKORDB_PORT", 6379))
FALKORDB_PASSWORD = os.getenv("FALKORDB_PASSWORD", None) or None
FALKORDB_GRAPH = os.getenv("FALKORDB_GRAPH", "smartcal")

_db = None
_graph = None


def get_graph():
    global _db, _graph
    if _graph is None:
        _db = FalkorDB(
            host=FALKORDB_HOST,
            port=FALKORDB_PORT,
            password=FALKORDB_PASSWORD,
        )
        _graph = _db.select_graph(FALKORDB_GRAPH)
    return _graph


def result_to_dicts(result) -> list[dict]:
    """Convert FalkorDB result to list of dicts."""
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


async def query(cypher: str, **params) -> list[dict]:
    """Execute a Cypher query and return results as dicts."""
    graph = get_graph()
    try:
        result = graph.query(cypher, params)
        return result_to_dicts(result)
    except Exception as e:
        return [{"error": str(e)}]
