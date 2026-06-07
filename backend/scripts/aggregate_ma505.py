"""Aggregate MA505 VdS Branchen-Codes to graph."""

import json
import sys
from collections import defaultdict, Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from common.database import get_graph

GRAPH_NAME = "dguv_v3"
STAND = "2026-06-01"


def main():
    with open("/tmp/batch_MA505_results.json") as f:
        results = json.load(f)

    valid = [r for r in results if "error" not in r]
    print(f"MA505: {len(valid)} valid results")

    # Aggregate Branchen-Codes
    branchen = defaultdict(lambda: {"count": 0, "prueftage": [], "maengel": []})

    for r in valid:
        code = r.get("branchen_code") or "unbekannt"
        bez = r.get("branchen_bezeichnung") or r.get("gebaeudetyp") or "?"
        key = f"{code}-{bez[:40]}"
        b = branchen[key]
        b["count"] += 1
        b["code"] = code
        b["bezeichnung"] = bez

        t = r.get("prueftage")
        if t:
            try:
                tf = float(str(t).replace(",", "."))
                if 0 < tf < 50:
                    b["prueftage"].append(tf)
            except (ValueError, TypeError):
                pass

        m = r.get("maengel_anzahl")
        if m is not None:
            try:
                b["maengel"].append(float(m))
            except (ValueError, TypeError):
                pass

    print(f"\nBranchen: {len(branchen)}")
    print(f"\nTop 15:")
    for key, data in sorted(branchen.items(), key=lambda x: -x[1]["count"])[:15]:
        tage = data["prueftage"]
        avg_t = f"{sum(tage)/len(tage):.1f}" if tage else "?"
        print(f"  {key:45s} n={data['count']:5d} avg_tage={avg_t}")

    # Load to graph
    graph = get_graph(GRAPH_NAME)

    # Don't clean existing statistik nodes — add MA505-specific ones
    graph.query("MATCH (n:VdSBranchenProfil) DETACH DELETE n")

    loaded = 0
    for key, data in branchen.items():
        if data["count"] < 5:
            continue

        tage = data["prueftage"]
        avg_tage = round(sum(tage) / len(tage), 1) if tage else 0
        avg_maengel = round(sum(data["maengel"]) / len(data["maengel"]), 1) if data["maengel"] else 0
        code = data.get("code", "?").replace("'", "")
        bez = data.get("bezeichnung", "?").replace("'", "\\'")

        try:
            graph.query(f"""
            CREATE (:VdSBranchenProfil {{
                id: 'VBP_{code}',
                branchen_code: '{code}',
                bezeichnung: '{bez}',
                n_berichte: {data['count']},
                avg_prueftage: {avg_tage},
                avg_maengel: {avg_maengel},
                _quelle: 'Batch Extraction {data["count"]} MA505 Berichte',
                _typ: 'statistik',
                _stand: '{STAND}'
            }})
            """)
            loaded += 1
        except Exception as e:
            print(f"  ERROR: {str(e)[:60]}")

    print(f"\nLoaded {loaded} VdSBranchenProfil nodes")

    # Final stats
    nodes = graph.query("MATCH (n) RETURN count(n) AS cnt").result_set[0][0]
    vds_nodes = graph.query("MATCH (n:VdSBranchenProfil) RETURN count(n) AS cnt").result_set[0][0]
    print(f"Graph total: {nodes} nodes ({vds_nodes} VdSBranchenProfil)")


if __name__ == "__main__":
    main()
