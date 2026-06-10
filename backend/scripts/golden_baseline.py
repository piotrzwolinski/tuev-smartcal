"""Golden-Baseline-Snapshot — Anti-Regressions-Vertrag (Plan v2, Phase 0.2).

Läuft alle Golden Sets durch die deterministische Python-PricingEngine und
schreibt tests/baseline_v1.json mit per-Case Ergebnis + Delta vs. Realpreis.

Determinismus: USE_GRAPH_PRICING wird auf 'false' gezwungen — alle Raten
kommen aus den Python-Fallback-Konstanten, kein FalkorDB nötig. Reisekosten
werden nicht berechnet (Golden-Merkmale ohne Koordinaten) — die Baseline
misst das Preismodell (grund + pruef + bericht), nicht Geocoding.

Usage:
    python scripts/golden_baseline.py                # schreibt tests/baseline_v1.json
    python scripts/golden_baseline.py --compare      # vergleicht aktuellen Stand vs. Baseline
    python scripts/golden_baseline.py --out PATH     # eigener Output-Pfad

Compare-Modus (Teststrategie #1): Exit-Code 1, wenn irgendein Case >2
Prozentpunkte schlechter ist (|delta| steigt) — "kein Case >2% schlechter
ohne dokumentierten Grund im Commit".
"""

import argparse
import json
import os
import subprocess
import sys
from datetime import date
from pathlib import Path

# Deterministisch: Python-Fallbacks statt Graph (vor Imports setzen!)
os.environ["USE_GRAPH_PRICING"] = "false"

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import products.blitzschutz  # noqa: F401  (register gewerk)
import products.dguv_v3  # noqa: F401
from engine.gewerk import get_gewerk
from engine.pricing_engine import PricingEngine

BASELINE_PATH = Path(__file__).resolve().parent.parent / "tests" / "baseline_v1.json"
PRODUCTS = ["blitzschutz", "dguv_v3"]
WORSE_THRESHOLD_PP = 2.0  # Prozentpunkte |delta|-Verschlechterung


def _git_rev() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=Path(__file__).resolve().parent.parent,
            text=True,
        ).strip()
    except Exception:
        return "unknown"


def run_golden(product: str) -> dict:
    gewerk = get_gewerk(product)
    engine = PricingEngine()
    golden = gewerk.golden_set()

    cases = []
    errors = 0
    for idx, (merkmale, real, ref) in enumerate(golden):
        try:
            angebot = engine.calculate(gewerk, merkmale)
        except Exception as e:  # Case soll Baseline nicht killen
            errors += 1
            cases.append({"i": idx, "ref": ref, "real": real, "error": str(e)})
            continue
        bd = angebot.breakdown
        delta_pct = ((angebot.total - real) / real * 100.0) if real else None
        cases.append({
            "i": idx,
            "ref": ref,
            "real": round(real, 2),
            "total": round(angebot.total, 2),
            "grund": round(bd.grund, 2),
            "pruef": round(bd.pruef, 2),
            "bericht": round(bd.bericht, 2),
            "delta_pct": round(delta_pct, 2) if delta_pct is not None else None,
        })

    deltas = [abs(c["delta_pct"]) for c in cases if c.get("delta_pct") is not None]
    deltas_sorted = sorted(deltas)
    summary = {
        "n": len(cases),
        "errors": errors,
        "mean_abs_delta_pct": round(sum(deltas) / len(deltas), 2) if deltas else None,
        "median_abs_delta_pct": round(deltas_sorted[len(deltas_sorted) // 2], 2) if deltas_sorted else None,
        "p90_abs_delta_pct": round(deltas_sorted[int(len(deltas_sorted) * 0.9)], 2) if deltas_sorted else None,
        "within_15pct": sum(1 for d in deltas if d <= 15),
        "within_30pct": sum(1 for d in deltas if d <= 30),
    }
    return {"cases": cases, "summary": summary}


def build_baseline() -> dict:
    out = {
        "version": "v1",
        "git_rev": _git_rev(),
        "created": date.today().isoformat(),
        "engine": "PricingEngine (Python-Fallbacks, USE_GRAPH_PRICING=false, ohne Reisekosten)",
        "products": {},
    }
    for product in PRODUCTS:
        result = run_golden(product)
        out["products"][product] = result
        s = result["summary"]
        print(f"  {product}: n={s['n']} errors={s['errors']} "
              f"mean|Δ|={s['mean_abs_delta_pct']}% median|Δ|={s['median_abs_delta_pct']}% "
              f"≤15%: {s['within_15pct']} ≤30%: {s['within_30pct']}")
        if s["n"] == 0:
            print(f"  ⚠ WARNUNG: Golden Set für '{product}' leer (Quelldatei fehlt?)")
    return out


def compare(baseline_path: Path) -> int:
    with open(baseline_path) as f:
        baseline = json.load(f)

    print(f"Vergleich gegen {baseline_path.name} (rev {baseline.get('git_rev')}, {baseline.get('created')})")
    exit_code = 0
    for product in PRODUCTS:
        base_cases = {c["ref"]: c for c in baseline["products"].get(product, {}).get("cases", [])}
        current = run_golden(product)
        worse, better, new_errors = [], 0, 0
        for c in current["cases"]:
            b = base_cases.get(c["ref"])
            if b is None:
                continue
            if "error" in c and "error" not in b:
                new_errors += 1
                worse.append((c["ref"], b.get("delta_pct"), f"ERROR: {c['error'][:60]}"))
                continue
            if c.get("delta_pct") is None or b.get("delta_pct") is None:
                continue
            diff_pp = abs(c["delta_pct"]) - abs(b["delta_pct"])
            if diff_pp > WORSE_THRESHOLD_PP:
                worse.append((c["ref"], b["delta_pct"], c["delta_pct"]))
            elif diff_pp < -WORSE_THRESHOLD_PP:
                better += 1
        print(f"\n{product}: {len(worse)} Cases >{WORSE_THRESHOLD_PP}pp schlechter, {better} besser, {new_errors} neue Errors")
        for ref, old_d, new_d in worse[:25]:
            print(f"  WORSE  {ref}")
            print(f"         Δ {old_d}% → {new_d}%")
        if len(worse) > 25:
            print(f"  ... und {len(worse) - 25} weitere")
        if worse:
            exit_code = 1
    return exit_code


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--compare", action="store_true", help="aktuellen Stand gegen Baseline vergleichen")
    ap.add_argument("--out", type=Path, default=BASELINE_PATH, help="Output-Pfad (default tests/baseline_v1.json)")
    args = ap.parse_args()

    if args.compare:
        sys.exit(compare(BASELINE_PATH))

    print("Erzeuge Golden-Baseline (deterministisch, ohne Graph/Reise)...")
    baseline = build_baseline()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with open(args.out, "w") as f:
        json.dump(baseline, f, indent=1, ensure_ascii=False)
    total_cases = sum(p["summary"]["n"] for p in baseline["products"].values())
    print(f"\n→ {args.out} geschrieben ({total_cases} Cases).")
    if total_cases == 0:
        print("✗ Keine Cases — Golden-Quelldateien fehlen. Baseline NICHT verwendbar.")
        sys.exit(1)


if __name__ == "__main__":
    main()
