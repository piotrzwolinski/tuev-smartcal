"""Load graph_schema.cypher into FalkorDB."""

import os
import sys
import time

from database import get_graph, FALKORDB_HOST, FALKORDB_PORT, FALKORDB_GRAPH

SCHEMA_PATH = os.path.join(os.path.dirname(__file__), "database", "graph_schema.cypher")


def load_schema(clear_first: bool = True) -> dict:
    """Load the Cypher schema file into the FalkorDB graph.

    Returns stats dict with counts.
    """
    graph = get_graph()

    if clear_first:
        try:
            graph.query("MATCH (n) DETACH DELETE n")
        except Exception:
            pass  # Graph might not exist yet

    with open(SCHEMA_PATH, "r") as f:
        content = f.read()

    # Strip comment lines, then split into individual statements
    lines = []
    for line in content.split("\n"):
        stripped = line.strip()
        if stripped.startswith("//") or stripped.startswith("--"):
            continue
        lines.append(line)
    cleaned = "\n".join(lines)

    statements = []
    for stmt in cleaned.split(";"):
        stmt = stmt.strip()
        if stmt and not stmt.upper().startswith("CREATE CONSTRAINT"):
            statements.append(stmt)

    executed = 0
    errors = []
    for i, stmt in enumerate(statements):
        try:
            graph.query(stmt)
            executed += 1
        except Exception as e:
            errors.append({"statement_index": i, "error": str(e), "cypher": stmt[:100]})

    # Get counts
    try:
        node_result = graph.query("MATCH (n) RETURN count(n) AS cnt")
        node_count = node_result.result_set[0][0] if node_result.result_set else 0
    except Exception:
        node_count = -1

    try:
        edge_result = graph.query("MATCH ()-[r]->() RETURN count(r) AS cnt")
        edge_count = edge_result.result_set[0][0] if edge_result.result_set else 0
    except Exception:
        edge_count = -1

    return {
        "graph": FALKORDB_GRAPH,
        "host": FALKORDB_HOST,
        "statements_total": len(statements),
        "statements_executed": executed,
        "errors": errors,
        "node_count": node_count,
        "edge_count": edge_count,
    }


if __name__ == "__main__":
    print(f"Loading schema into FalkorDB graph '{FALKORDB_GRAPH}' at {FALKORDB_HOST}:{FALKORDB_PORT}...")
    t0 = time.time()
    stats = load_schema()
    elapsed = round(time.time() - t0, 2)

    print(f"\nDone in {elapsed}s")
    print(f"  Statements: {stats['statements_executed']}/{stats['statements_total']}")
    print(f"  Nodes: {stats['node_count']}")
    print(f"  Edges: {stats['edge_count']}")

    if stats["errors"]:
        print(f"\n  Errors ({len(stats['errors'])}):")
        for err in stats["errors"][:10]:
            print(f"    [{err['statement_index']}] {err['error']}")
            print(f"        {err['cypher']}")

    sys.exit(0 if not stats["errors"] else 1)
