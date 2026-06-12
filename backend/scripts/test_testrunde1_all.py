"""Run ALL 16 Testrunde-1 cases through the v4 pricing engine.

Prints comparison table: v1 (original) vs v2 (current) vs Real.
v4 changes: Augsburg power-law regression, Kombi=DGUV×1.20, Kat 7 Krankenhaus, size guards.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from unittest.mock import patch
from products.dguv_v3.merkmale import (
    DGUVMerkmale, GebaeudeNutzungDGUV, Installationskategorie,
    Pruefart, NutzungsMixEintrag,
)
from engine.pricing_engine import PricingEngine
from engine.gewerk import get_gewerk

import products.dguv_v3  # noqa: register
import products.blitzschutz  # noqa: register


# Mock standort to isolate Reisekosten
STANDORT_MAP = {
    "85276": {"id": "MUC", "name": "München", "plz": "80686", "adresse": "Westendstr. 199", "distance_km": 45, "duration_min": 35, "routing": "mock"},
    "85386": {"id": "MUC", "name": "München", "plz": "80686", "adresse": "Westendstr. 199", "distance_km": 30, "duration_min": 25, "routing": "mock"},
    "77933": {"id": "FRB", "name": "Freiburg", "plz": "79108", "adresse": "Hermann-Mitsch-Str. 36A", "distance_km": 5, "duration_min": 8, "routing": "mock"},
    "68167": {"id": "MAN", "name": "Mannheim", "plz": "68167", "adresse": "diverse", "distance_km": 10, "duration_min": 12, "routing": "mock"},
    "93444": {"id": "RGB", "name": "Regensburg", "plz": "93051", "adresse": "Friedenstr. 6", "distance_km": 60, "duration_min": 50, "routing": "mock"},
    "32105": {"id": "BIE", "name": "Bielefeld", "plz": "33602", "adresse": "Herforder Str.", "distance_km": 25, "duration_min": 20, "routing": "mock"},
    "01445": {"id": "DRS", "name": "Dresden", "plz": "01069", "adresse": "Wiener Platz 10", "distance_km": 15, "duration_min": 18, "routing": "mock"},
    "80331": {"id": "MUC", "name": "München", "plz": "80686", "adresse": "Westendstr. 199", "distance_km": 5, "duration_min": 8, "routing": "mock"},
    "83209": {"id": "TRS", "name": "Traunstein", "plz": "83301", "adresse": "Empfinger Str. 6", "distance_km": 34, "duration_min": 32, "routing": "mock"},
    "97080": {"id": "WUE", "name": "Würzburg", "plz": "97080", "adresse": "Petrinstr. 33A", "distance_km": 2, "duration_min": 4, "routing": "mock"},
    "85221": {"id": "MUC", "name": "München", "plz": "80686", "adresse": "Westendstr. 199", "distance_km": 17, "duration_min": 26, "routing": "mock"},
    "82205": {"id": "MUC", "name": "München", "plz": "80686", "adresse": "Westendstr. 199", "distance_km": 25, "duration_min": 22, "routing": "mock"},
    "81249": {"id": "MUC", "name": "München", "plz": "80686", "adresse": "Westendstr. 199", "distance_km": 10, "duration_min": 15, "routing": "mock"},
    "85540": {"id": "MUC", "name": "München", "plz": "80686", "adresse": "Westendstr. 199", "distance_km": 20, "duration_min": 18, "routing": "mock"},
    "75365": {"id": "FLD", "name": "Filderstadt", "plz": "70794", "adresse": "Gottlieb-Daimler-Str. 7", "distance_km": 55, "duration_min": 47, "routing": "mock"},
}

PLZ_COORDS = {
    "85276": (48.53, 11.49),   # Pfaffenhofen (Hipp)
    "85386": (48.30, 11.62),   # Eching (REWE)
    "77933": (48.16, 7.85),    # Lahr (badenova)
    "68167": (49.49, 8.47),    # Mannheim
    "93444": (49.32, 12.38),   # Kötzing
    "32105": (52.02, 8.53),    # Bad Salzuflen (Maritim)
    "01445": (51.11, 13.65),   # Radebeul (K&B)
    "80331": (48.14, 11.57),   # München Zentrum (Motel One)
    "83209": (47.85, 12.34),   # Prien (roMEd)
    "97080": (49.80, 9.95),    # Würzburg
    "85221": (48.26, 11.44),   # Dachau
    "82205": (48.11, 11.30),   # Gilching (Apleona)
    "81249": (48.14, 11.45),   # München-Pasing (Helios)
    "85540": (48.14, 11.51),   # Haar (REWE München)
    "75365": (48.71, 8.73),    # Calw
}


def _mock_standort(lat, lon):
    best = None
    best_dist = 999999
    for plz, (plat, plon) in PLZ_COORDS.items():
        dist = abs(lat - plat) + abs(lon - plon)
        if dist < best_dist:
            best_dist = dist
            best = plz
    return STANDORT_MAP.get(best, STANDORT_MAP["80331"])


def run_case(case_id, label, merkmale, real_price, v1_price, note="", referenz_jahr=None):
    gewerk = get_gewerk("dguv_v3")
    engine = PricingEngine()
    try:
        angebot = engine.calculate(gewerk, merkmale)
        total = angebot.total
        pruef = angebot.breakdown.pruef
        grund = angebot.breakdown.grund
        reise = angebot.breakdown.reise
        bericht = angebot.breakdown.bericht
        conf = angebot.confidence

        real_adj = real_price
        if referenz_jahr and real_price and real_price > 0:
            from products.dguv_v3.pricing_rules import inflate_to_current
            real_adj = inflate_to_current(real_price, referenz_jahr)

        if real_adj and real_adj > 0:
            delta_v2 = (total - real_adj) / real_adj * 100
            delta_v1 = (v1_price - real_adj) / real_adj * 100 if v1_price else None
        else:
            delta_v2 = None
            delta_v1 = None

        return {
            "id": case_id, "label": label, "real": real_price, "v1": v1_price,
            "real_adj": real_adj if referenz_jahr else None,
            "referenz_jahr": referenz_jahr,
            "v2_total": total, "v2_pruef": pruef, "v2_grund": grund,
            "v2_reise": reise, "v2_bericht": bericht, "conf": conf,
            "delta_v2": delta_v2, "delta_v1": delta_v1, "note": note,
            "warnings": [w for w in angebot.warnings if "Empfehlung" not in w],
        }
    except Exception as e:
        return {
            "id": case_id, "label": label, "real": real_price, "v1": v1_price,
            "v2_total": None, "note": f"ERROR: {e}",
        }


@patch("common.pricing_primitives.find_nearest_standort", side_effect=_mock_standort)
def main(mock_standort):
    cases = []

    # ═══ ZIP CASES (Pausch XLSX) ═══

    # T01 — ZIP-1: Hipp Pfaffenhofen, VdS, 20k m², 45 UV, 8000 kVA
    cases.append(run_case("T01", "Hipp Pfaffenhofen (VdS)", DGUVMerkmale(
        nutzung=GebaeudeNutzungDGUV.INDUSTRIE,
        pruefart=Pruefart.VDS,
        gesamtflaeche_m2=20000,
        anzahl_verteilungen_uv=45,
        primary_installationskategorie=Installationskategorie.KAT_3,
        adresse_lat=48.53, adresse_lon=11.49,
        adresse_plz="85276",
    ), real_price=6850, v1_price=11877, note="MA505 VdS"))

    # T02 — ZIP-2: REWE Eching, 800m²
    cases.append(run_case("T02", "REWE Eching (RV)", DGUVMerkmale(
        nutzung=GebaeudeNutzungDGUV.VERKAUFSSTAETTE,
        gesamtflaeche_m2=800,
        adresse_lat=48.30, adresse_lon=11.62,
        adresse_plz="85386",
    ), real_price=657.26, v1_price=2125.28, note="RV-Filialnetz flat"))

    # T03 — ZIP-3: badenova, 1 Schaltschrank, PLZ 77933
    cases.append(run_case("T03", "badenova Schaltschrank", DGUVMerkmale(
        nutzung=GebaeudeNutzungDGUV.SONSTIGE,
        anzahl_verteilungen_nshv=1,
        adresse_lat=48.16, adresse_lon=7.85,
        adresse_plz="77933",
    ), real_price=391, v1_price=1051.06, note="Kleinauftrag"))

    # T04 — ZIP-4: Auto Service Calw, 114 BM, MA560
    cases.append(run_case("T04", "Auto Service Calw (MA560)", DGUVMerkmale(
        nutzung=GebaeudeNutzungDGUV.INDUSTRIE,
        pruefart=Pruefart.DGUV_ORTSVERAENDERLICH,
        anzahl_betriebsmittel=114,
        adresse_lat=48.71, adresse_lon=8.73,
        adresse_plz="75365",
    ), real_price=1216.95, v1_price=1198.33, note="PASS in Runde 1"))

    # T05 — ZIP-5: Landwirt Neukirchen, 23 BM
    cases.append(run_case("T05", "Landwirt Neukirchen (MA560)", DGUVMerkmale(
        nutzung=GebaeudeNutzungDGUV.INDUSTRIE,
        pruefart=Pruefart.DGUV_ORTSVERAENDERLICH,
        anzahl_betriebsmittel=23,
        adresse_lat=49.32, adresse_lon=12.38,
        adresse_plz="93444",
    ), real_price=174.80, v1_price=1400, note="Ref DEFEKT (Pausch)"))

    # T06 — ZIP-6: Maritim Hotel, MA510, 40 UV, 100 Zimmer
    cases.append(run_case("T06", "Maritim Hotel (MA510)", DGUVMerkmale(
        nutzung=GebaeudeNutzungDGUV.HOTEL,
        gesamtflaeche_m2=3000,  # 100 Zimmer × 30
        anzahl_verteilungen_uv=40,
        adresse_lat=52.02, adresse_lon=8.53,
        adresse_plz="32105",
    ), real_price=220, v1_price=4063.50, note="Ref DEFEKT + MA510 OOS"))

    # T07 — ZIP-7: König & Bauer Radebeul, 48 UV, 4 Gebäude, 900 m²
    cases.append(run_case("T07", "König & Bauer (VdS)", DGUVMerkmale(
        nutzung=GebaeudeNutzungDGUV.INDUSTRIE,
        pruefart=Pruefart.VDS,
        gesamtflaeche_m2=900,
        anzahl_verteilungen_uv=48,
        nutzungs_mix=[
            NutzungsMixEintrag(nutzung="Produktion", anteil=0.80, kategorie=Installationskategorie.KAT_3),
            NutzungsMixEintrag(nutzung="Verwaltung", anteil=0.20, kategorie=Installationskategorie.KAT_2),
        ],
        adresse_lat=51.11, adresse_lon=13.65,
        adresse_plz="01445",
    ), real_price=None, v1_price=None, note="Nicht getestet in R1"))

    # ═══ PPT CASES (Weiß Screenshots) ═══

    # T08 — PPT-1: Apleona Gilching, 26k m², 37 UV, DGUV+VdS
    cases.append(run_case("T08", "Apleona Gilching (DGUV+VdS)", DGUVMerkmale(
        nutzung=GebaeudeNutzungDGUV.BUEROGEBAEUDE,
        pruefart=Pruefart.DGUV_PLUS_VDS,
        gesamtflaeche_m2=26000,
        anzahl_verteilungen_uv=37,
        adresse_lat=48.11, adresse_lon=11.30,
        adresse_plz="82205",
    ), real_price=7932, v1_price=10370, note="v1 nach Rückfragen→23982"))

    # T09 — PPT-2: Weber-Gymnasium, Multi (BMA+SiBel+ELT)
    cases.append(run_case("T09", "Weber-Gymnasium (MULTI)", DGUVMerkmale(
        nutzung=GebaeudeNutzungDGUV.SCHULE,
        gesamtflaeche_m2=5000,
        adresse_lat=48.15, adresse_lon=11.57,
        adresse_plz="80331",
    ), real_price=4800, v1_price=2834, note="Multi=MVP, nur ELT-Anteil"))

    # T10 — PPT-3: Max Planck RZ Garching, 545 BM
    cases.append(run_case("T10", "Max Planck RZ (MA560)", DGUVMerkmale(
        nutzung=GebaeudeNutzungDGUV.INDUSTRIE,
        pruefart=Pruefart.DGUV_ORTSVERAENDERLICH,
        anzahl_betriebsmittel=545,
        adresse_lat=48.26, adresse_lon=11.67,
        adresse_plz="85540",
    ), real_price=5341, v1_price=2084, note="v1 nach Rückfragen"))

    # T11 — PPT-4: REWE München, ~1600m²
    cases.append(run_case("T11", "REWE München (RV)", DGUVMerkmale(
        nutzung=GebaeudeNutzungDGUV.VERKAUFSSTAETTE,
        gesamtflaeche_m2=1600,
        adresse_lat=48.14, adresse_lon=11.51,
        adresse_plz="85540",
    ), real_price=657.26, v1_price=1738.54, note="RV flat wie T02"))

    # T12 — PPT-5: Helios Klinik Pasing, DGUV+VdS
    cases.append(run_case("T12", "Helios Klinik (DGUV+VdS)", DGUVMerkmale(
        nutzung=GebaeudeNutzungDGUV.KRANKENHAUS,
        pruefart=Pruefart.DGUV_PLUS_VDS,
        gesamtflaeche_m2=18000,
        nutzungs_mix=[
            NutzungsMixEintrag(nutzung="Allgemein", anteil=0.70, kategorie=Installationskategorie.KAT_2),
            NutzungsMixEintrag(nutzung="Technik/OP", anteil=0.30, kategorie=Installationskategorie.KAT_7),
        ],
        adresse_lat=48.14, adresse_lon=11.45,
        adresse_plz="81249",
    ), real_price=13110, v1_price=10840, note="54h×239€"))

    # ═══ DOC CASES (Burgey DOCX) ═══

    # T13 — DOC-1: Motel One München, MA501
    cases.append(run_case("T13", "Motel One München (RV)", DGUVMerkmale(
        nutzung=GebaeudeNutzungDGUV.HOTEL,
        gesamtflaeche_m2=6000,  # ~200 Zimmer × 30
        adresse_lat=48.14, adresse_lon=11.57,
        adresse_plz="80331",
    ), real_price=621, v1_price=5161.31, note="RV 2023"))

    # T14 — DOC-2: roMEd Klinik Prien, MA501
    cases.append(run_case("T14", "roMEd Klinik Prien", DGUVMerkmale(
        nutzung=GebaeudeNutzungDGUV.KRANKENHAUS,
        gesamtflaeche_m2=8000,
        nutzungs_mix=[
            NutzungsMixEintrag(nutzung="Allgemein", anteil=0.70, kategorie=Installationskategorie.KAT_2),
            NutzungsMixEintrag(nutzung="Technik", anteil=0.30, kategorie=Installationskategorie.KAT_7),
        ],
        adresse_lat=47.85, adresse_lon=12.34,
        adresse_plz="83209",
    ), real_price=3470, v1_price=4322.74, referenz_jahr=2012, note="inflationsbereinigt (2012→2026)"))

    # T15 — DOC-3: DGUV Würzburg, MA507
    cases.append(run_case("T15", "DGUV Würzburg", DGUVMerkmale(
        nutzung=GebaeudeNutzungDGUV.BUEROGEBAEUDE,
        gesamtflaeche_m2=5000,
        adresse_lat=49.80, adresse_lon=9.95,
        adresse_plz="97080",
    ), real_price=4195.25, v1_price=3282.37, note="Braucht mehr Merkmale"))

    # T16 — DOC-4: Polizei Dachau, Blitz MA574
    # Using Blitz gewerk separately
    try:
        from products.blitzschutz.merkmale import BlitzschutzMerkmale, GebaeudeNutzung
        blitz_gewerk = get_gewerk("blitzschutz")
        m = BlitzschutzMerkmale(
            nutzung=GebaeudeNutzung.SONSTIGE,
            anzahl_ableitungen=12,
            adresse_lat=48.26, adresse_lon=11.44,
            adresse_plz="85221",
        )
        engine = PricingEngine()
        angebot = engine.calculate(blitz_gewerk, m)
        cases.append({
            "id": "T16", "label": "Polizei Dachau (Blitz)", "real": 205,
            "v1": 1536.66, "v2_total": angebot.total, "v2_pruef": angebot.breakdown.pruef,
            "v2_grund": angebot.breakdown.grund, "v2_reise": angebot.breakdown.reise,
            "v2_bericht": angebot.breakdown.bericht, "conf": angebot.confidence,
            "delta_v2": (angebot.total - 205) / 205 * 100,
            "delta_v1": (1536.66 - 205) / 205 * 100,
            "note": "RV, Blitz-Produkt", "warnings": angebot.warnings,
        })
    except Exception as e:
        cases.append({"id": "T16", "label": "Polizei Dachau (Blitz)", "real": 205,
                       "v1": 1536.66, "v2_total": None, "note": f"Blitz ERROR: {e}"})

    # ═══ REPORT ═══

    print("=" * 120)
    print("TESTRUNDE 1 — ALLE 16 CASES — v4 ENGINE RESULTS")
    print("=" * 120)
    print()
    print(f"{'ID':<5} {'Label':<32} {'Real':>8} {'v1':>8} {'v2':>8} {'Δv1':>7} {'Δv2':>7} {'Verdict':<12} {'Note'}")
    print("-" * 120)

    pass_count = 0
    rv_count = 0
    xfail_count = 0
    total_testable = 0

    for c in cases:
        real = c.get("real")
        real_adj = c.get("real_adj")
        v1 = c.get("v1")
        v2 = c.get("v2_total")

        if real_adj:
            real_s = f"{real_adj:,.0f}*"
        elif real:
            real_s = f"{real:,.0f}"
        else:
            real_s = "—"
        v1_s = f"{v1:,.0f}" if v1 else "—"
        v2_s = f"{v2:,.0f}" if v2 else "ERR"

        dv1 = c.get("delta_v1")
        dv2 = c.get("delta_v2")
        dv1_s = f"{dv1:+.0f}%" if dv1 is not None else "—"
        dv2_s = f"{dv2:+.0f}%" if dv2 is not None else "—"

        note = c.get("note", "")

        # Verdict logic
        if "DEFEKT" in note or "MULTI" in note.upper():
            verdict = "xfail"
            xfail_count += 1
        elif "RV" in note and real and v2 and v2 > real:
            verdict = "RV-FLAG"
            rv_count += 1
            total_testable += 1
        elif real and v2 and abs(dv2) <= 20:
            verdict = "PASS"
            pass_count += 1
            total_testable += 1
        elif real and v2 and abs(dv2) <= 35:
            verdict = "MARGINAL"
            total_testable += 1
        elif real and v2:
            verdict = "FAIL"
            total_testable += 1
        elif not real:
            verdict = "NO-REF"
        else:
            verdict = "ERR"

        print(f"{c['id']:<5} {c['label']:<32} {real_s:>8} {v1_s:>8} {v2_s:>8} {dv1_s:>7} {dv2_s:>7} {verdict:<12} {note}")

    print("-" * 120)
    print()

    # Detailed breakdown
    print("DETAIL — BREAKDOWN (v2)")
    print(f"{'ID':<5} {'Grund':>8} {'Prüf':>8} {'Reise':>8} {'Bericht':>8} {'Total':>8} {'Conf':>5} {'Warnings'}")
    print("-" * 120)
    for c in cases:
        if c.get("v2_total") is None:
            print(f"{c['id']:<5} {'—':>8} {'—':>8} {'—':>8} {'—':>8} {'—':>8} {'—':>5} {c.get('note','')}")
            continue
        w = "; ".join(c.get("warnings", [])[:2])
        if len(w) > 50:
            w = w[:50] + "…"
        print(f"{c['id']:<5} {c.get('v2_grund',0):>8,.0f} {c.get('v2_pruef',0):>8,.0f} "
              f"{c.get('v2_reise',0):>8,.0f} {c.get('v2_bericht',0):>8,.0f} "
              f"{c.get('v2_total',0):>8,.0f} {c.get('conf',0)*100:>4.0f}% {w}")
    print()

    # Summary
    print("=" * 60)
    print(f"PASS (≤20%):     {pass_count}")
    print(f"MARGINAL (≤35%): —")
    print(f"RV-FLAG:         {rv_count}")
    print(f"xfail (OOS):     {xfail_count}")
    managed = pass_count + rv_count
    print(f"MANAGED:         {managed}/{total_testable} ({managed/total_testable*100:.0f}%)" if total_testable else "")
    print(f"v1 PASS rate:    2/14 (14%)")
    print("=" * 60)


if __name__ == "__main__":
    main()
