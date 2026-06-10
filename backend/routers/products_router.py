"""Cross-product meta-router: /api/products/*."""

from fastapi import APIRouter

from engine.gewerk import list_gewerke, get_gewerk, _REGISTRY


router = APIRouter(prefix="/api/products", tags=["products"])


@router.get("")
async def list_products():
    """Manifest of all registered products."""
    return {
        "phase": 1,
        "products": list_gewerke(),
        "phase_1_scope": {
            "blitzschutz": "MA570 umfassend (Veit-primary, golden set 325 Anlagen)",
            "rlt": "MA419 (Hygiene VDI 6022 + Garagenlüftung)",
            "dguv_v3": "MA507 ortsfest (Veit-benchmark)",
        },
        "phase_2_candidates": [
            "MA572 Blitzschutz Baurecht Sonderbau",
            "MA574 Blitzschutz wiederkehrend",
            "MA555 Blitzschutz Ex-Schutz",
            "MA438 NRA Rauchabzug",
            "MA441 BSK Brandschutzklappen",
            "MA501 Elektr. Anl. Ex",
            "MA510 Starkstrom Sonderbau",
            "MA560 Ortsveränderliche Geräte",
        ],
    }


@router.get("/{gewerk_id}")
async def product_metadata(gewerk_id: str):
    try:
        g = get_gewerk(gewerk_id)
    except KeyError:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=f"Unknown gewerk: {gewerk_id}")
    return {
        "id": g.id,
        "name": g.name,
        "ma_codes": g.ma_codes,
        "lpv_referenz": g.lpv_referenz,
        "graph_name": g.graph_name,
        "merkmale_schema": g.merkmale_schema.model_json_schema(),
    }
