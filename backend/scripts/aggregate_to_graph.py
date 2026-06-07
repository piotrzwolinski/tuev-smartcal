"""Aggregate batch extraction results → BranchenProfil + FeatureZuschlag nodes in FalkorDB.

Input: /tmp/batch_MA507_results.json (+ MA560, MA510, MA501)
Output: New graph nodes with _typ='statistik' in dguv_v3 graph
"""

import json
import sys
from collections import defaultdict, Counter
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from common.database import get_graph

GRAPH_NAME = "dguv_v3"
STAND = "2026-06-01"


def load_results(material: str) -> list[dict]:
    data_dir = Path.home() / "Desktop/TUEV/_extracted"
    path = data_dir / f"batch_{material}_results.json"
    if not path.exists():
        path = data_dir / "batch_500er_full_results.json"
        if not path.exists():
            print(f"  ⚠ No results file for {material}")
            return []
        with open(path) as f:
            all_results = json.load(f)
        return [r for r in all_results if r.get("material") == material and "error" not in r]

    with open(path) as f:
        results = json.load(f)
    return [r for r in results if "error" not in r]


def safe_float(v):
    if v is None:
        return None
    try:
        return float(str(v).replace(",", ".").replace("%", "").strip())
    except (ValueError, TypeError):
        return None


def percentile(data, p):
    if not data:
        return 0
    s = sorted(data)
    k = (len(s) - 1) * p / 100
    f = int(k)
    c = f + 1 if f + 1 < len(s) else f
    return s[f] + (k - f) * (s[c] - s[f])


def aggregate_ma507(results: list[dict]) -> dict:
    """Aggregate MA507 results into BranchenProfile + FeatureZuschläge."""

    # Filter Gesamtanlagen only
    gesamt = [r for r in results if r.get("ist_gesamtanlage") is True]
    teil = [r for r in results if r.get("ist_gesamtanlage") is False]
    print(f"  Gesamtanlagen: {len(gesamt)}, Teilanlagen: {len(teil)} (excluded)")

    # --- BRANCHEN PROFILE ---
    branchen = defaultdict(lambda: {
        "prueftage": [],
        "seitenzahl": [],
        "maengel": [],
        "raeume": Counter(),
        "anlagen": Counter(),
        "doku_zustand": Counter(),
        "vorheriger_bericht": {"true": 0, "false": 0},
        "erschwernisse": Counter(),
        "count": 0,
    })

    for r in gesamt:
        branche = r.get("betreiber_branche") or r.get("gebaeudetyp") or "sonstige"
        branche = branche.strip()
        if not branche or branche.lower() == "null":
            branche = "sonstige"
        b = branchen[branche]
        b["count"] += 1

        t = safe_float(r.get("prueftage"))
        if t and 0 < t < 50:
            b["prueftage"].append(t)

        s = safe_float(r.get("seitenzahl"))
        if s and s > 0:
            b["seitenzahl"].append(s)

        m = safe_float(r.get("maengel_anzahl"))
        if m is not None:
            b["maengel"].append(m)

        disc = r.get("_discovery", {})

        for raum, cnt in (disc.get("raeume_typen") or {}).items():
            b["raeume"][raum] += 1

        for anlage in (disc.get("erwaehnte_anlagen") or []):
            b["anlagen"][anlage] += 1

        doku = disc.get("dokumentation_zustand")
        if doku:
            b["doku_zustand"][doku] += 1

        vorher = disc.get("vorheriger_pruefbericht")
        if vorher is True:
            b["vorheriger_bericht"]["true"] += 1
        elif vorher is False:
            b["vorheriger_bericht"]["false"] += 1

        for e in (disc.get("erschwernisse") or []):
            b["erschwernisse"][e] += 1

    # --- FEATURE ZUSCHLÄGE (cross-branche) ---
    feature_tage = defaultdict(lambda: {"with": [], "without": []})

    all_features_found = Counter()
    for r in gesamt:
        ausstattung = set(r.get("besondere_ausstattung") or [])
        disc_anlagen = set((r.get("_discovery", {}).get("erwaehnte_anlagen") or []))
        all_features = ausstattung | disc_anlagen

        for f in all_features:
            all_features_found[f] += 1

        t = safe_float(r.get("prueftage"))
        if not t or t > 50:
            continue

        for feature in all_features:
            feature_tage[feature]["with"].append(t)

    # Calculate "without" for each feature
    all_tage = [safe_float(r.get("prueftage")) for r in gesamt if safe_float(r.get("prueftage")) and safe_float(r.get("prueftage")) < 50]
    avg_all = sum(all_tage) / len(all_tage) if all_tage else 2.0

    feature_zuschlaege = {}
    for feature, data in feature_tage.items():
        w = data["with"]
        if len(w) < 5:
            continue
        avg_with = sum(w) / len(w)
        faktor = avg_with / avg_all if avg_all > 0 else 1.0
        feature_zuschlaege[feature] = {
            "faktor": round(faktor, 2),
            "n_mit": len(w),
            "avg_prueftage_mit": round(avg_with, 1),
            "avg_prueftage_ohne": round(avg_all, 1),
        }

    # --- SEITENZAHL → PRÜFTAGE KORRELATION ---
    seiten_tage = defaultdict(list)
    for r in gesamt:
        t = safe_float(r.get("prueftage"))
        s = safe_float(r.get("seitenzahl"))
        if not t or not s or t > 50:
            continue
        bucket = "1-3" if s <= 3 else "4-6" if s <= 6 else "7-10" if s <= 10 else "11+"
        seiten_tage[bucket].append(t)

    return {
        "branchen": dict(branchen),
        "feature_zuschlaege": feature_zuschlaege,
        "seiten_tage": {k: {"avg": round(sum(v)/len(v), 1), "n": len(v)} for k, v in seiten_tage.items()},
        "total_gesamt": len(gesamt),
        "total_teil": len(teil),
        "top_features": all_features_found.most_common(20),
    }


def aggregate_ma560(results: list[dict]) -> dict:
    """Aggregate MA560: Gebäudetyp → Geräte-Count."""
    typ_geraete = defaultdict(list)
    for r in results:
        typ = r.get("gebaeudetyp") or "sonstige"
        g = safe_float(r.get("anzahl_gepruefte_geraete"))
        if g and g > 0:
            typ_geraete[typ].append(g)

    profiles = {}
    for typ, geraete in typ_geraete.items():
        if len(geraete) < 3:
            continue
        profiles[typ] = {
            "avg": round(sum(geraete) / len(geraete)),
            "median": round(percentile(geraete, 50)),
            "p25": round(percentile(geraete, 25)),
            "p75": round(percentile(geraete, 75)),
            "min": round(min(geraete)),
            "max": round(max(geraete)),
            "n": len(geraete),
        }
    return {"geraete_profile": profiles}


def load_to_graph(ma507_agg: dict, ma560_agg: dict):
    """Load aggregated statistics as graph nodes."""
    graph = get_graph(GRAPH_NAME)

    # Clean old statistik nodes
    graph.query("MATCH (n) WHERE n._typ = 'statistik' DETACH DELETE n")
    print("  Cleaned old statistik nodes")

    statements = []

    # --- BRANCHEN PROFILE ---
    for branche, data in ma507_agg["branchen"].items():
        if data["count"] < 5:
            continue

        tage = data["prueftage"]
        avg_tage = round(sum(tage) / len(tage), 1) if tage else 0
        median_tage = round(percentile(tage, 50), 1) if tage else 0
        p25_tage = round(percentile(tage, 25), 1) if tage else 0
        p75_tage = round(percentile(tage, 75), 1) if tage else 0

        avg_maengel = round(sum(data["maengel"]) / len(data["maengel"]), 1) if data["maengel"] else 0

        # Typische Räume (top 5)
        top_raeume = dict(data["raeume"].most_common(5))
        raeume_json = json.dumps(top_raeume, ensure_ascii=False).replace("'", "\\'")

        # Typische Anlagen (top 5)
        top_anlagen = dict(data["anlagen"].most_common(5))
        anlagen_json = json.dumps(top_anlagen, ensure_ascii=False).replace("'", "\\'")

        # Doku-Zustand
        total_doku = sum(data["doku_zustand"].values()) or 1
        doku_vollst = data["doku_zustand"].get("vorhanden_vollstaendig", 0)
        doku_unvollst = data["doku_zustand"].get("vorhanden_unvollstaendig", 0)
        doku_nicht = data["doku_zustand"].get("nicht_vorhanden", 0)

        # Vorgeschlagener Reifegrad
        if doku_vollst / total_doku > 0.6:
            vorgeschl_rg = 3
        elif doku_unvollst / total_doku > 0.5:
            vorgeschl_rg = 2
        elif doku_nicht / total_doku > 0.3:
            vorgeschl_rg = 1
        else:
            vorgeschl_rg = 3

        # Vorheriger Prüfbericht %
        total_vorher = data["vorheriger_bericht"]["true"] + data["vorheriger_bericht"]["false"]
        pct_vorher = round(data["vorheriger_bericht"]["true"] / total_vorher * 100) if total_vorher > 0 else 0

        branche_escaped = branche.replace("'", "\\'").replace('"', '\\"')

        statements.append(f"""
        CREATE (:BranchenProfil {{
            id: 'BP_{hash(branche) % 100000}',
            branche: '{branche_escaped}',
            n_berichte: {data['count']},
            avg_prueftage: {avg_tage},
            median_prueftage: {median_tage},
            p25_prueftage: {p25_tage},
            p75_prueftage: {p75_tage},
            avg_maengel: {avg_maengel},
            typische_raeume: '{raeume_json}',
            typische_anlagen: '{anlagen_json}',
            doku_vollstaendig_pct: {round(doku_vollst/total_doku*100)},
            doku_unvollstaendig_pct: {round(doku_unvollst/total_doku*100)},
            vorgeschlagener_reifegrad: {vorgeschl_rg},
            vorheriger_pruefbericht_pct: {pct_vorher},
            _quelle: 'Batch Extraction {data["count"]} MA507 Berichte',
            _typ: 'statistik',
            _stand: '{STAND}'
        }})
        """)

    # --- FEATURE ZUSCHLÄGE ---
    for feature, data in ma507_agg["feature_zuschlaege"].items():
        feature_escaped = feature.replace("'", "\\'")
        statements.append(f"""
        CREATE (:FeatureZuschlag {{
            id: 'FZ_{hash(feature) % 100000}',
            feature: '{feature_escaped}',
            faktor: {data['faktor']},
            n_mit: {data['n_mit']},
            avg_prueftage_mit: {data['avg_prueftage_mit']},
            avg_prueftage_gesamt: {data['avg_prueftage_ohne']},
            _quelle: 'Batch Extraction / Feature-Korrelation',
            _typ: 'statistik',
            _stand: '{STAND}'
        }})
        """)

    # --- SEITEN → PRÜFTAGE ---
    for bucket, data in ma507_agg["seiten_tage"].items():
        statements.append(f"""
        CREATE (:SeitenKorrelation {{
            id: 'SK_{bucket.replace("-","_").replace("+","plus")}',
            seiten_range: '{bucket}',
            avg_prueftage: {data['avg']},
            n: {data['n']},
            _quelle: 'Batch Extraction / Seitenzahl-Korrelation',
            _typ: 'statistik',
            _stand: '{STAND}'
        }})
        """)

    # --- MA560 GERÄTE-PROFILE ---
    if ma560_agg:
        for typ, data in ma560_agg.get("geraete_profile", {}).items():
            typ_escaped = typ.replace("'", "\\'")
            statements.append(f"""
            CREATE (:GeraeteProfil {{
                id: 'GP_{hash(typ) % 100000}',
                gebaeudetyp: '{typ_escaped}',
                avg_geraete: {data['avg']},
                median_geraete: {data['median']},
                p25_geraete: {data['p25']},
                p75_geraete: {data['p75']},
                min_geraete: {data['min']},
                max_geraete: {data['max']},
                n_berichte: {data['n']},
                _quelle: 'Batch Extraction MA560',
                _typ: 'statistik',
                _stand: '{STAND}'
            }})
            """)

    # Execute
    loaded = 0
    errors = 0
    for stmt in statements:
        try:
            graph.query(stmt.strip())
            loaded += 1
        except Exception as e:
            errors += 1
            print(f"  ERROR: {str(e)[:80]}")

    print(f"  Loaded {loaded} nodes, {errors} errors")

    # Stats
    stats = graph.query("MATCH (n) WHERE n._typ = 'statistik' RETURN labels(n)[0] AS l, count(n) AS c ORDER BY c DESC")
    print("  Statistik-Nodes im Graph:")
    for row in stats.result_set:
        print(f"    {row[0]:25s} {row[1]:4d}")


def main():
    print("=== Loading MA507 results ===")
    ma507_results = load_results("MA507")
    print(f"  {len(ma507_results)} valid results")

    print("\n=== Aggregating MA507 ===")
    ma507_agg = aggregate_ma507(ma507_results) if ma507_results else {}

    if ma507_agg:
        print(f"  Branchen: {len(ma507_agg['branchen'])}")
        print(f"  Feature-Zuschläge: {len(ma507_agg['feature_zuschlaege'])}")
        print(f"  Top Features: {ma507_agg['top_features'][:10]}")

        print("\n  Top Branchen (by count):")
        for branche, data in sorted(ma507_agg["branchen"].items(), key=lambda x: -x[1]["count"])[:10]:
            tage = data["prueftage"]
            avg_t = round(sum(tage)/len(tage), 1) if tage else "?"
            print(f"    {branche:35s} n={data['count']:4d} avg_tage={avg_t}")

        print("\n  Feature-Zuschläge (faktor):")
        for feature, data in sorted(ma507_agg["feature_zuschlaege"].items(), key=lambda x: -x[1]["faktor"])[:10]:
            print(f"    {feature:25s} ×{data['faktor']:.2f} (n={data['n_mit']})")

    print("\n=== Loading MA560 results ===")
    ma560_results = load_results("MA560")
    print(f"  {len(ma560_results)} valid results")

    ma560_agg = aggregate_ma560(ma560_results) if ma560_results else {}

    if ma560_agg:
        print("\n  Geräte-Profile per Gebäudetyp:")
        for typ, data in sorted(ma560_agg.get("geraete_profile", {}).items(), key=lambda x: -x[1]["n"]):
            print(f"    {typ:25s} avg={data['avg']:5d} median={data['median']:5d} range={data['min']}-{data['max']} (n={data['n']})")

    print("\n=== Loading to Graph ===")
    load_to_graph(ma507_agg, ma560_agg)

    # Final graph stats
    graph = get_graph(GRAPH_NAME)
    nodes = graph.query("MATCH (n) RETURN count(n) AS cnt").result_set[0][0]
    edges = graph.query("MATCH ()-[r]->() RETURN count(r) AS cnt").result_set[0][0]
    print(f"\n  Graph total: {nodes} nodes, {edges} edges")


if __name__ == "__main__":
    main()
