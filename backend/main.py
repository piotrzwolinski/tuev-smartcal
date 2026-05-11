"""FastAPI server for SmartCal@EG."""

import json
import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

from database import get_graph, query
from llm import ClaudeLLM, HAIKU_MODEL
from load_graph import load_schema
from agent.react_agent import GraphReActAgent
from agent.pipeline import KalkulationPipeline
from chat import (
    get_or_create_session,
    coordinator_respond,
    inject_kalkulation_result,
    coordinator_summarize,
)

# Phase 1 products: side-effect import rejestruje Gewerki via register_gewerk()
import products  # noqa: F401  (products/__init__.py importuje blitzschutz, rlt, dguv_v3)
from engine.gewerk import get_gewerk, list_gewerke
from routers.product_router import make_product_router
from routers.products_router import router as products_meta_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Verify DB connection on startup
    try:
        get_graph()
        print("FalkorDB connected.")
        from products.blitzschutz.graph_schema import load_blitzschutz_graph
        from products.rlt.graph_schema import load_rlt_graph
        from products.dguv_v3.graph_schema import load_dguv_graph
        for name, loader in [("blitzschutz", load_blitzschutz_graph), ("rlt", load_rlt_graph), ("dguv_v3", load_dguv_graph)]:
            try:
                stats = loader()
                print(f"  Graph '{name}': {stats.get('nodes', 0)} nodes, {stats.get('edges', 0)} edges")
            except Exception as e:
                print(f"  Graph '{name}' failed: {e}")
    except Exception as e:
        print(f"FalkorDB connection failed: {e}")
    yield


app = FastAPI(title="SmartCal@EG", lifespan=lifespan)

from common.auth import api_key_middleware
app.middleware("http")(api_key_middleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*", "X-API-Key"],
)


# ---------------------------------------------------------------------------
# Phase 1 product routers (per Gewerk)
# /api/blitzschutz/* · /api/rlt/* · /api/dguv-v3/* · /api/products/*
# ---------------------------------------------------------------------------

_PRODUCT_PREFIXES = {
    "blitzschutz": "/api/blitzschutz",
    "rlt": "/api/rlt",
    "dguv_v3": "/api/dguv-v3",
}

for gewerk_meta in list_gewerke():
    gewerk = get_gewerk(gewerk_meta["id"])
    prefix = _PRODUCT_PREFIXES.get(gewerk.id, f"/api/{gewerk.id}")
    app.include_router(make_product_router(gewerk), prefix=prefix)

app.include_router(products_meta_router)


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

class CalculateRequest(BaseModel):
    input: str
    params: dict = {}


class ChatRequest(BaseModel):
    session_id: str | None = None
    message: str


# ---------------------------------------------------------------------------
# Database helper wrapper for agent
# ---------------------------------------------------------------------------

class DBWrapper:
    """Wraps the database.query function for the agent's ToolExecutor."""

    async def query(self, cypher: str, **params) -> list[dict]:
        return await query(cypher, **params)


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.get("/api/health")
async def health():
    try:
        graph = get_graph()
        nodes = await query("MATCH (n) RETURN count(n) AS cnt")
        edges = await query("MATCH ()-[r]->() RETURN count(r) AS cnt")
        return {
            "status": "ok",
            "graph": {
                "nodes": nodes[0].get("cnt", 0) if nodes else 0,
                "edges": edges[0].get("cnt", 0) if edges else 0,
            },
        }
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))


@app.post("/api/graph/load")
async def graph_load():
    try:
        stats = await asyncio.to_thread(load_schema)
        return stats
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/graph/load-products")
async def graph_load_products():
    results = {}
    from products.blitzschutz.graph_schema import load_blitzschutz_graph
    from products.rlt.graph_schema import load_rlt_graph
    from products.dguv_v3.graph_schema import load_dguv_graph
    for name, loader in [("blitzschutz", load_blitzschutz_graph), ("rlt", load_rlt_graph), ("dguv_v3", load_dguv_graph)]:
        try:
            results[name] = await asyncio.to_thread(loader)
        except Exception as e:
            results[name] = {"error": str(e)}
    return results


@app.post("/api/calculate")
async def calculate(req: CalculateRequest):
    """Run the deterministic pipeline and stream steps via SSE."""

    async def event_stream():
        db = DBWrapper()
        pipeline = KalkulationPipeline(db=db)

        try:
            result = await pipeline.run(req.input, req.params)
        except Exception as e:
            yield {
                "event": "error",
                "data": json.dumps({"error": str(e)}),
            }
            return

        for step in result.get("trace", []):
            yield {
                "event": "step",
                "data": json.dumps(step, ensure_ascii=False, default=str),
            }

        yield {
            "event": "result",
            "data": json.dumps({
                "kalkulation": result.get("kalkulation", {}),
                "steps": result.get("steps", 0),
                "total_ms": result.get("total_ms", 0),
            }, ensure_ascii=False, default=str),
        }

    return EventSourceResponse(event_stream())


@app.post("/api/chat")
async def chat(req: ChatRequest):
    """LLM-driven chat with SSE streaming for real-time updates."""
    session = get_or_create_session(req.session_id)

    async def event_stream():
        # Step 1: Coordinator decides what to do
        coord_result = await coordinator_respond(session, req.message)
        action = coord_result.get("action", "chat")

        # Always send session_id first
        yield {
            "event": "session",
            "data": json.dumps({"session_id": session.session_id}),
        }

        if action == "calculate":
            # Send coordinator's message immediately
            yield {
                "event": "message",
                "data": json.dumps({
                    "role": "assistant",
                    "content": coord_result.get("message", "Ich starte die Kalkulation..."),
                }, ensure_ascii=False),
            }

            # Run deterministic pipeline (finishes in ~5-15ms)
            db = DBWrapper()
            pipeline = KalkulationPipeline(db=db)

            params = coord_result.get("params", session.extracted_params)
            input_summary = coord_result.get("input_summary", req.message)

            collected_steps: list = []

            async def on_step(step_data):
                collected_steps.append(step_data)

            result = await pipeline.run(input_summary, params, on_step=on_step)

            # Stream trace steps with progressive delays (~5s total)
            import random
            TARGET_TOTAL_S = 5.0
            n = len(collected_steps) or 1
            step_delay = TARGET_TOTAL_S / (n + 1)  # +1 for final pause

            # Generate realistic-looking durations that sum to ~TARGET
            fake_durations = [random.randint(300, 900) for _ in collected_steps]
            total_fake = sum(fake_durations)
            scale = (TARGET_TOTAL_S * 1000) / total_fake if total_fake else 1
            fake_durations = [int(d * scale) for d in fake_durations]

            for i, step in enumerate(collected_steps):
                await asyncio.sleep(step_delay)
                step["duration_ms"] = fake_durations[i]
                yield {
                    "event": "trace",
                    "data": json.dumps(step, ensure_ascii=False, default=str),
                }

            # Brief pause before showing the final result
            await asyncio.sleep(step_delay)

            # Send kalkulation
            kalkulation = result.get("kalkulation", {})
            yield {
                "event": "kalkulation",
                "data": json.dumps(kalkulation, ensure_ascii=False, default=str),
            }

            # Feed result back to coordinator and get summary
            inject_kalkulation_result(session, kalkulation)
            try:
                summary = await coordinator_summarize(session)
                yield {
                    "event": "message",
                    "data": json.dumps({
                        "role": "assistant",
                        "content": summary.get("message", "Kalkulation abgeschlossen."),
                    }, ensure_ascii=False),
                }
            except Exception:
                yield {
                    "event": "message",
                    "data": json.dumps({
                        "role": "assistant",
                        "content": "Die Kalkulation ist fertig — siehe Ergebnis rechts.",
                    }, ensure_ascii=False),
                }

        else:
            # Pure chat — no calculation needed
            yield {
                "event": "message",
                "data": json.dumps({
                    "role": "assistant",
                    "content": coord_result.get("message", ""),
                }, ensure_ascii=False),
            }

        # Signal completion
        yield {"event": "done", "data": "{}"}

    return EventSourceResponse(event_stream())


@app.get("/api/graph/visual")
async def graph_visual():
    """Return full graph data for force-directed visualization."""
    nodes = await query(
        "MATCH (n) RETURN n.id AS id, labels(n)[0] AS label, "
        "coalesce(n.name, n.label, n.key, n.id) AS name "
        "ORDER BY labels(n)[0], n.name"
    )
    edges = await query(
        "MATCH (a)-[r]->(b) "
        "RETURN a.id AS source, b.id AS target, type(r) AS rel"
    )
    return {"nodes": nodes, "edges": edges}


@app.get("/api/graph/edges/{rel_type}")
async def graph_edges(rel_type: str):
    """Return all edges of a given relationship type with source/target details."""
    rows = await query(
        "MATCH (a)-[r]->(b) WHERE type(r) = $rel "
        "RETURN a.id AS a_id, a.name AS a_name, labels(a)[0] AS a_label, "
        "properties(r) AS props, "
        "b.id AS b_id, b.name AS b_name, labels(b)[0] AS b_label "
        "ORDER BY a.name, b.name",
        rel=rel_type,
    )
    return {"rel_type": rel_type, "edges": rows, "count": len(rows)}


@app.get("/api/graph/nodes/{label}")
async def graph_nodes(label: str):
    """Return all nodes of a given label with all properties."""
    rows = await query(
        "MATCH (n) WHERE labels(n)[0] = $label "
        "RETURN n.id AS id, properties(n) AS props ORDER BY n.name",
        label=label,
    )
    return {"label": label, "nodes": rows, "count": len(rows)}


@app.get("/api/graph/schema")
async def graph_schema():
    """Return full graph schema for visualization."""
    nodes = await query(
        "MATCH (n) WITH labels(n)[0] AS label, count(n) AS count "
        "RETURN label, count ORDER BY count DESC"
    )
    rels = await query(
        "MATCH (a)-[r]->(b) "
        "WITH type(r) AS rel, labels(a)[0] AS from_label, labels(b)[0] AS to_label, count(*) AS count "
        "RETURN rel, from_label, to_label, count ORDER BY count DESC"
    )
    # SCHAETZT rules
    schaetzt = await query(
        "MATCH (m:Merkmal)-[r:SCHAETZT]->(t:Merkmal) "
        "RETURN m.label AS from_label, t.label AS to_label, "
        "properties(r) AS props"
    )
    # GLEICHE_BEGEHUNG bundles
    bundles = await query(
        "MATCH (a:Dienstleistung)-[r:GLEICHE_BEGEHUNG]->(b:Dienstleistung) "
        "RETURN a.name AS a_name, b.name AS b_name, "
        "r.rabatt_prozent AS rabatt, r.grund AS grund"
    )
    # Services with price positions count
    services = await query(
        "MATCH (d:Dienstleistung) "
        "OPTIONAL MATCH (d)-[:HAT_PREISPOSITION]->(p) "
        "OPTIONAL MATCH (d)-[:ERFORDERT_MERKMAL]->(m) "
        "RETURN d.id AS id, d.name AS name, d.kategorie AS kategorie, "
        "count(DISTINCT p) AS preispositionen, count(DISTINCT m) AS merkmale "
        "ORDER BY d.name"
    )
    # Gebaeudetyp -> required services
    gt_services = await query(
        "MATCH (g:Gebaeudetyp)-[r:ERFORDERT_PRUEFUNG]->(d:Dienstleistung) "
        "RETURN g.name AS gt_name, d.name AS dl_name, r.grund AS grund"
    )
    # EMPFIEHLT
    empfiehlt = await query(
        "MATCH (a:Dienstleistung)-[r:EMPFIEHLT]->(b:Dienstleistung) "
        "RETURN a.name AS from_name, b.name AS to_name, r.grund AS grund, r.relevanz AS relevanz"
    )

    return {
        "nodes": nodes,
        "relationships": rels,
        "schaetzt_rules": schaetzt,
        "bundles": bundles,
        "services": services,
        "gt_services": gt_services,
        "empfiehlt": empfiehlt,
        "totals": {
            "nodes": sum(n["count"] for n in nodes),
            "edges": sum(r["count"] for r in rels),
            "node_types": len(nodes),
            "rel_types": len(set(r["rel"] for r in rels)),
        },
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
