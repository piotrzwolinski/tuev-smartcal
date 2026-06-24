#!/usr/bin/env python3
"""Kalibrier-Pipeline — reale Faktura (Isterlös) × Anlagenmerkmale → Preismodell.

Verbindet:
  1. Versand-Export Faktura (sources/data/files/versand_export_24_06/{507,560}-WP_final.xlsx)
     → EQ → realer Isterlös.
  2. Merkmale je EQ (scripts/calibration_merkmale.csv) — wächst, sobald mehr
     Prüfberichte extrahiert sind (7 neue PDFs + Schmieder + Batch der 10k MA507).
  3. Schmieder-Listenpreise (505, kVA-getrieben).
→ Fittet pro Segment:
     • DGUV-507  Preis ≈ a + b·UV   (Schule/Hochschule)
     • MA560     €/Gerät über Mengenbänder (Degression P2)
     • VdS-505   Preis ~ kVA (Krankenhaus, Schmieder)
und stellt jeder Stützstelle das AKTUELLE Modell (phantom-m²) gegenüber.

Lauf:  ./venv/bin/python scripts/calibrate_pricing.py
Output: Konsolen-Report + scripts/calibration_result.json
Erweitern: neue Zeile in calibration_merkmale.csv → erneut laufen.
"""
import csv
import json
import os

import numpy as np
import openpyxl

HERE = os.path.dirname(os.path.abspath(__file__))
EXPORT = os.path.join(HERE, "..", "..", "sources", "data", "files", "versand_export_24_06")
MERKMALE = os.path.join(HERE, "calibration_merkmale.csv")

# Schmieder-Campus-Listenpreise (RV-flat, aus Preisliste 18.06 — nicht im Faktura-Export)
SCHMIEDER_505 = {"1268813": 2151, "1268824": 5880, "1879930": 5880, "2122743": 655}

# Aktuelles Modell (UI/phantom-m², live getestet) zum Vergleich
CURRENT = {"2065503": 2577, "1484135": 7812, "2427833": 4850, "2490109": 549,
           "2229803": 8275, "2597657": 1283, "3578607": 419, "3295815": None}


def load_faktura(fn):
    """EQ → neuester Isterlös (>0)."""
    wb = openpyxl.load_workbook(os.path.join(EXPORT, fn), read_only=True, data_only=True)
    ws = wb[wb.sheetnames[0]]
    by_eq = {}
    for r in list(ws.iter_rows(values_only=True))[1:]:
        if r[3] is None:
            continue
        try:
            v = float(r[5]) if r[5] is not None else 0
        except (TypeError, ValueError):
            v = 0
        if v > 0:
            by_eq.setdefault(str(r[3]), []).append((str(r[4]), v))
    wb.close()
    return {eq: sorted(vs)[-1][1] for eq, vs in by_eq.items()}  # neuester


def load_merkmale():
    rows = []
    with open(MERKMALE, encoding="utf-8") as f:
        for d in csv.DictReader(f):
            if d["eq"].startswith("#"):
                continue
            rows.append(d)
    return rows


def _num(s):
    try:
        return float(s) if s not in (None, "") else None
    except ValueError:
        return None


def fit_linear(xs, ys):
    b, a = np.polyfit(xs, ys, 1)
    pred = [a + b * x for x in xs]
    ss_res = sum((y - p) ** 2 for y, p in zip(ys, pred))
    ss_tot = sum((y - np.mean(ys)) ** 2 for y in ys)
    r2 = 1 - ss_res / ss_tot if ss_tot else 0
    return a, b, r2


def main():
    p507 = load_faktura("507-WP_final.xlsx")
    p560 = load_faktura("560-WP_final.xlsx")
    merk = load_merkmale()
    result = {"segments": {}}

    def price(eq, mat):
        if mat == "507":
            return p507.get(eq)
        if mat == "560":
            return p560.get(eq)
        if mat == "505":
            return SCHMIEDER_505.get(eq)
        return None

    print("=" * 78)
    print("KALIBRIER-PIPELINE — reale Faktura × Merkmale")
    print(f"Faktura geladen: 507={len(p507)} EQ · 560={len(p560)} EQ · Merkmale-Tabelle={len(merk)} EQ")
    print("=" * 78)

    # ── Segment DGUV-507 per-UV (Schule/Hochschule) ──
    seg = [(m, price(m["eq"], "507")) for m in merk
           if m["material"] == "507" and m["gebaeudetyp"] in ("schule", "hochschule")
           and _num(m["uv"]) is not None and price(m["eq"], "507")]
    if len(seg) >= 2:
        xs = [_num(m["uv"]) for m, _ in seg]
        ys = [pr for _, pr in seg]
        a, b, r2 = fit_linear(xs, ys)
        print(f"\n■ DGUV-507 · Schule/Hochschule:  Preis ≈ {a:.0f} € + {b:.1f} €/UV   (R²={r2:.2f}, n={len(seg)})")
        print(f"  {'EQ':<9}{'Typ':<11}{'UV':>4}{'Real':>8}{'Fit':>8}{'Δ':>6}   {'akt. Modell':>12}")
        for (m, pr), x in zip(seg, xs):
            fit = a + b * x
            cur = CURRENT.get(m["eq"])
            curs = f"{cur:.0f} ({(cur-pr)/pr*100:+.0f}%)" if cur else "—"
            print(f"  {m['eq']:<9}{m['gebaeudetyp']:<11}{x:>4.0f}{pr:>8.0f}{fit:>8.0f}{(fit-pr)/pr*100:>5.0f}%   {curs:>12}")
        result["segments"]["dguv507_per_uv"] = {"base_eur": round(a, 1), "eur_per_uv": round(b, 1), "r2": round(r2, 3), "n": len(seg)}

    # Produktion (anderer Typ) separat
    for m in merk:
        if m["material"] == "507" and m["gebaeudetyp"] == "produktion":
            pr = price(m["eq"], "507")
            print(f"\n  ⚠ Produktion (anderer Typ, separat): EQ {m['eq']} · 1 UV · Real {pr:.0f} € "
                  f"(passt nicht auf Schul-Gerade — eigener Satz nötig)")

    # ── Segment MA560 per-BM (Degression P2) ──
    seg = [(m, price(m["eq"], "560")) for m in merk
           if m["material"] == "560" and _num(m["bm"]) and price(m["eq"], "560")]
    seg = [(m, pr) for m, pr in seg if "defekt" not in m["quelle"].lower()]
    if seg:
        print(f"\n■ MA560 · €/Gerät über Mengenbänder (Degression?):")
        print(f"  {'EQ':<9}{'BM':>5}{'Real':>8}{'€/BM':>8}   Modell 200+9,50/BM")
        rows560 = []
        for m, pr in sorted(seg, key=lambda t: _num(t[0]["bm"])):
            bm = _num(m["bm"])
            model = 200 + bm * 9.50
            print(f"  {m['eq']:<9}{bm:>5.0f}{pr:>8.0f}{pr/bm:>8.2f}   {model:.0f} ({(model-pr)/pr*100:+.0f}%)")
            rows560.append({"eq": m["eq"], "bm": bm, "real": pr, "eur_per_bm": round(pr/bm, 2)})
        result["segments"]["ma560_per_bm"] = rows560
        print("  → €/BM fällt mit Menge (Degression/RV-flat) → Staffel statt flat 9,50.")

    # ── Segment VdS-505 kVA (Schmieder Krankenhaus) ──
    seg = [(m, price(m["eq"], "505")) for m in merk
           if m["material"] == "505" and _num(m["kva"]) and price(m["eq"], "505")]
    if seg:
        print(f"\n■ VdS-505 · Krankenhaus-Campus ~ kVA (Schmieder):")
        print(f"  {'EQ':<9}{'kVA':>6}{'Preis':>8}{'€/kVA':>8}")
        for m, pr in sorted(seg, key=lambda t: _num(t[0]["kva"])):
            kva = _num(m["kva"])
            print(f"  {m['eq']:<9}{kva:>6.0f}{pr:>8.0f}{pr/kva:>8.2f}")
        result["segments"]["vds505_kva"] = [{"eq": m["eq"], "kva": _num(m["kva"]), "preis": pr} for m, pr in seg]

    out = os.path.join(HERE, "calibration_result.json")
    json.dump(result, open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print(f"\n→ {out}")
    print("\nErweitern: neue EQ+Merkmale in calibration_merkmale.csv → erneut laufen (mehr Stützstellen).")


if __name__ == "__main__":
    main()
