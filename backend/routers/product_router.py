"""Generic product router factory.

Tworzy APIRouter dla dowolnego Gewerku — identyczne endpointy:
  POST /calculate
  POST /anfrage/parse
  GET  /anlage/{id}
  GET  /stats
  GET  /validate

Usage:
    from routers.product_router import make_product_router
    from products.blitzschutz import BLITZSCHUTZ
    router = make_product_router(BLITZSCHUTZ)
    app.include_router(router, prefix="/api/blitzschutz")
"""

import asyncio
import json

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, ValidationError
from sse_starlette.sse import EventSourceResponse

from engine.gewerk import Gewerk
from engine.pricing_engine import PricingEngine
from engine.validator import run_validation
from common.database import get_graph, query


class ChatRequest(BaseModel):
    session_id: str | None = None
    message: str
    mode: str = "graph"  # "graph" | "python"


def make_product_router(gewerk: Gewerk) -> APIRouter:
    router = APIRouter(tags=[gewerk.id])
    engine = PricingEngine()

    @router.get("/health")
    async def health():
        return {
            "status": "ok",
            "gewerk": gewerk.name,
            "ma_codes": gewerk.ma_codes,
            "lpv_referenz": gewerk.lpv_referenz,
            "graph_name": gewerk.graph_name,
        }

    @router.post("/calculate")
    async def calculate(payload: dict, mode: str = Query(default="graph", enum=["python", "graph"])):
        try:
            merkmale = gewerk.merkmale_schema(**payload)
        except ValidationError as e:
            raise HTTPException(status_code=422, detail=e.errors())

        if mode == "graph":
            from engine.graph_pricing_engine import GraphPricingEngine
            graph_engine = GraphPricingEngine(gewerk.graph_name)
            angebot = graph_engine.calculate(gewerk, merkmale)
            result = angebot.to_dict()
            result["mode"] = "graph"
            result["provenance"] = graph_engine.provenance
        else:
            angebot = engine.calculate(gewerk, merkmale)
            result = angebot.to_dict()
            result["mode"] = "python"
            result["provenance"] = []

        return result

    @router.post("/anfrage/parse")
    async def parse_anfrage(payload: dict):
        """TODO M5.1: LLM-based natural-language → Merkmale parser."""
        text = payload.get("text", "")
        return {
            "status": "not_implemented_yet",
            "note": "Phase 1 M5.1 (KW20): parse natural-language Anfrage → Merkmale",
            "input_text": text[:200],
        }

    @router.get("/stats")
    async def stats():
        """Graph stats for this Gewerk."""
        try:
            nodes = await query("MATCH (n) RETURN count(n) AS cnt", graph_name=gewerk.graph_name)
            edges = await query("MATCH ()-[r]->() RETURN count(r) AS cnt", graph_name=gewerk.graph_name)
            return {
                "gewerk": gewerk.id,
                "graph": gewerk.graph_name,
                "nodes": nodes[0].get("cnt", 0) if nodes else 0,
                "edges": edges[0].get("cnt", 0) if edges else 0,
            }
        except Exception as e:
            return {"gewerk": gewerk.id, "error": str(e)}

    @router.get("/validate")
    async def validate(sample: int = Query(default=50, ge=1, le=1000)):
        """Run validation against golden set."""
        try:
            report = run_validation(gewerk.id, sample=sample)
            return {
                "gewerk": gewerk.id,
                "summary": report.summary(),
                "sample_size": report.sample_size,
                "total_tested": report.total_tested,
                "match_rate_5pct": report.match_rate_5,
                "match_rate_10pct": report.match_rate_10,
                "match_rate_20pct": report.match_rate_20,
                "avg_delta_pct": report.avg_delta_pct,
                "median_delta_pct": report.median_delta_pct,
                "outliers": [
                    {
                        "ref": o.anlage_reference,
                        "calculated": o.calculated_price,
                        "expected": o.expected_price,
                        "delta_pct": o.delta_pct,
                    }
                    for o in report.outliers
                ],
            }
        except NotImplementedError:
            return {
                "gewerk": gewerk.id,
                "status": "golden_set_not_loaded_yet",
                "note": "Golden set loader TODO (M2.4 / M3.3 / M3.4)",
            }

    @router.get("/schema")
    async def schema():
        """Return Pydantic schema of Merkmale (JSONSchema)."""
        return gewerk.merkmale_schema.model_json_schema()

    @router.get("/anlage/{anlage_id}")
    async def get_anlage(anlage_id: str):
        """Fetch Anlage from graph by ID."""
        rows = await query(
            "MATCH (a:Anlage {id: $id}) RETURN a",
            graph_name=gewerk.graph_name,
            id=anlage_id,
        )
        if not rows:
            raise HTTPException(status_code=404, detail="Anlage not found")
        return {"anlage": rows[0]}

    # ───────────────────────────────────────────────────
    # Chat endpoint (SSE stream) — per Gewerk coordinator
    # ───────────────────────────────────────────────────
    @router.post("/chat")
    async def chat(req: ChatRequest):
        """Natural-language chat: coordinator extract Merkmale → calculate → summarize."""
        # Dynamic import — per-Gewerk chat module (opcjonalne)
        try:
            chat_module = __import__(
                f"products.{gewerk.id}.chat",
                fromlist=["get_or_create_session", "coordinator_respond",
                          "inject_kalkulation_result", "coordinator_summarize"],
            )
        except ImportError:
            raise HTTPException(status_code=501, detail=f"Chat not implemented for {gewerk.id}")

        session = chat_module.get_or_create_session(req.session_id)

        async def event_stream():
            yield {"event": "session", "data": json.dumps({"session_id": session.session_id})}

            coord = await chat_module.coordinator_respond(session, req.message)
            action = coord.get("action", "chat")
            import logging
            logging.getLogger(__name__).warning(f"[CHAT] Turn {session.turn_count}: action={action}, params_keys={list(coord.get('params', {}).keys())}")

            if action != "calculate":
                yield {"event": "message", "data": json.dumps({
                    "role": "assistant",
                    "content": coord.get("message", ""),
                }, ensure_ascii=False)}

            if action == "calculate":
                params = {k: v for k, v in coord.get("params", {}).items() if v is not None}

                # Stream "trace" events — user widzi kroki
                yield {"event": "trace", "data": json.dumps({"step": "extract", "label": "Merkmale extrahiert", "payload": params}, ensure_ascii=False)}
                await asyncio.sleep(0.3)

                # Validate Merkmale
                try:
                    merkmale = gewerk.merkmale_schema(**params)
                except ValidationError as e:
                    yield {"event": "message", "data": json.dumps({
                        "role": "assistant",
                        "content": f"Mir fehlen noch Angaben: {e.errors()[0].get('loc', ['?'])[0]}. Bitte nenne mir diese Information.",
                    }, ensure_ascii=False)}
                    yield {"event": "done", "data": "{}"}
                    return

                yield {"event": "trace", "data": json.dumps({"step": "validate", "label": "Pydantic Schema-Validation ✓"})}
                await asyncio.sleep(0.3)

                # Calculate (with mode switch)
                mode_label = "Graph-Engine (Wissensgraph)" if req.mode == "graph" else "Python-Engine (hardcoded)"
                yield {"event": "trace", "data": json.dumps({"step": "pricing", "label": f"{mode_label} · {gewerk.lpv_referenz}"})}
                await asyncio.sleep(0.3)

                if req.mode == "graph":
                    from engine.graph_pricing_engine import GraphPricingEngine
                    calc_engine = GraphPricingEngine(gewerk.graph_name)
                    angebot = calc_engine.calculate(gewerk, merkmale)

                    # Stream each provenance step as trace event
                    for prov in calc_engine.provenance:
                        step_name = prov["step"]
                        source = prov["source"]
                        value = prov["value"]
                        node_id = prov.get("node_id", "")

                        # Human-readable descriptions (like old smartcal demo)
                        if step_name == "grundkosten":
                            label = f"Graph → {source}: {value}€"
                        elif step_name == "prueftage":
                            label = f"⚠ Prüftage-Schätzung: {value} Tage [HEURISTIK — Rückfrage an TÜV]"
                        elif step_name == "tagegeld":
                            label = f"Graph → {source}: {value}€"
                        elif step_name == "pruefkosten":
                            is_heuristik = "heuristik" in str(source).lower()
                            label = f"{'⚠ ' if is_heuristik else 'Graph → '}{source}: {value}€{' [HEURISTIK]' if is_heuristik else ''}"
                        elif step_name == "reisekosten":
                            label = f"Graph → {source}"
                        elif step_name == "bericht":
                            label = f"⚠ {source}: {value}€ [Schwelle HEURISTIK — Rückfrage an TÜV]"
                        elif step_name == "zuschlag":
                            label = f"Graph → {source} = {value}"
                        elif step_name == "confidence":
                            label = f"Graph → {source}"
                        elif step_name == "kalibrierung":
                            label = f"📊 {source}"
                        elif step_name == "cross_sell":
                            label = f"Graph → Empfehlung: {str(value)[:60]}"
                        else:
                            label = f"Graph → {source}"

                        ref = prov.get("ref", "")
                        yield {"event": "trace", "data": json.dumps({
                            "step": step_name,
                            "label": label,
                            "payload": {"node_id": node_id, "value": str(value)[:50], "ref": ref},
                        }, ensure_ascii=False)}
                        await asyncio.sleep(0.15)

                    angebot_dict = angebot.to_dict()
                    angebot_dict["mode"] = "graph"
                    angebot_dict["provenance"] = calc_engine.provenance
                else:
                    calc_engine = PricingEngine()
                    angebot = calc_engine.calculate(gewerk, merkmale)
                    angebot_dict = angebot.to_dict()
                    angebot_dict["mode"] = "python"
                    angebot_dict["provenance"] = []

                yield {"event": "trace", "data": json.dumps({"step": "confidence", "label": f"Confidence Score: {angebot.confidence*100:.0f}%"})}
                await asyncio.sleep(0.2)

                # Emit full Angebot
                yield {"event": "angebot", "data": json.dumps(angebot_dict, ensure_ascii=False)}

                # Feed back to coordinator dla podsumowania
                chat_module.inject_kalkulation_result(session, angebot_dict)
                summary = await chat_module.coordinator_summarize(session)
                content = summary.get("message", "Kalkulation abgeschlossen.")
                # LLM sometimes returns raw JSON string — extract message field
                if isinstance(content, str) and content.strip().startswith("{"):
                    try:
                        parsed = json.loads(content)
                        content = parsed.get("message", content)
                    except (json.JSONDecodeError, AttributeError):
                        pass
                yield {"event": "message", "data": json.dumps({
                    "role": "assistant",
                    "content": content,
                }, ensure_ascii=False)}

            yield {"event": "done", "data": "{}"}

        return EventSourceResponse(event_stream())

    return router
