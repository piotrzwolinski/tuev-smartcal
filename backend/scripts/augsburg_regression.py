#!/usr/bin/env python3
"""
Augsburg Stadtwerke pricing regression analysis.
Fits power-law curves: price = a * m²^b per Nutzungstyp.
"""

import re
import numpy as np
import pandas as pd
from collections import defaultdict

EXCEL_PATH = "/Users/piotrzwolinski/projects/tuev/input-files/05_Preislisten_Grosskunden/Augsburg_StV_VdS_UVV.xlsx"

# Classification rules: category -> list of substrings (case-insensitive)
CLASSIFICATION_RULES = [
    # Order matters — first match wins
    ("kindergarten", [
        "kinder", "kita", "hort", "krippe", "kinderhaus", "kindernest",
        "kindertageseinrichtung", "kindertagesstätte", "kindertagesbetreuung",
        "willkommenskita", "krabbelgruppe",
    ]),
    ("schule", [
        "schule", "gymnasium", "realschule", "fos", "fachoberschule",
        "berufsschule", "fachakademie", "schullandheim", "schulverkehrsgarten",
        "schulungsraum", "sing- und musikschule",
    ]),
    ("turnhalle", [
        "turnhalle", "sporthalle",
    ]),
    ("sport", [
        "schwimm", "stadion", "sport", "bad", "hallenbad", "sommerbad",
        "freibad", "eisstadion", "plärrerbad", "spickelbad", "stadtbad",
        "reiterhof", "minigolf", "mini-golf", "bundesleistungszentrum",
        "athleten-center",
    ]),
    ("museum_kultur", [
        "museum", "bibliothek", "kulturhaus", "kino", "liliom",
        "puppenkiste", "kunsthalle", "glaspalast", "schaezler",
        "mozarthaus", "leopold-mozart", "brechthaus", "holbeinhaus",
        "höhmannhaus", "goldener saal", "halle 116",
    ]),
    ("verwaltung", [
        "rathaus", "amt ", "tiefbauamt", "veterineramt", "polizei",
    ]),
    ("buerogebaeude", [
        "büro", "verwaltungsgebäude", "verwaltungsgeb", "dienstgebäude",
        "dienstgeb", "betriebsgebäude",
    ]),
    ("versorgung", [
        "stadtwerke", "gaswerk", "wasserwerk", "klärwerk", "pumpwerk",
        "heizwerk", "heizkraftwerk", "biomasse", "kraftwerk",
        "gasturbine", "leitstelle", "übergabestation",
    ]),
    ("werkstatt", [
        "werkstatt", "werkstätten", "bauhof", "betriebshof", "werkmeisterei",
        "zentralwerkstatt", "stützpunkt",
    ]),
    ("depot_lager", [
        "lager", "depot", "magazin", "zwischenlager",
    ]),
    ("tiefgarage", [
        "tiefgarage", "parkhaus", "parkhäusle",
    ]),
    ("wohnung", [
        "wohn", "haus der stadt",  # but not "rathaus"
    ]),
    ("altenheim", [
        "altenheim", "altenstift", "stift", "pfründe", "fürsorge",
        "jakobsstift", "servatius", "sanderstiftung", "antonspfründe",
    ]),
    ("friedhof", [
        "friedhof", "leichenhaus",
    ]),
    ("gastronomie", [
        "gaststätte", "gastronomie", "cafe", "kiosk", "kahnfahrt",
        "campinghaus",
    ]),
    ("versammlungsstaette", [
        "stadthalle", "kongress", "bürgerhaus", "jugendhaus",
        "jugendzentrum", "jugendtreff",
    ]),
    ("stadtmarkt", [
        "stadtmarkt", "markt",
    ]),
    ("infrastruktur", [
        "straßenbahn", "straßenbahnhalle", "königsplatz",
        "wc-anlage", "deponie",
    ]),
    ("forst_garten", [
        "forst", "stadtgärtnerei", "pflanzgarten", "waldarbeiter",
        "grünordnung",
    ]),
    ("sonstiges", []),  # fallback
]


def classify_building(name: str) -> str:
    """Classify a building name into a Nutzungstyp."""
    name_lower = name.lower().strip()
    for category, keywords in CLASSIFICATION_RULES:
        if category == "sonstiges":
            return "sonstiges"
        for kw in keywords:
            if kw in name_lower:
                return category
    return "sonstiges"


def fit_power_law(m2_arr, price_arr):
    """
    Fit price = a * m2^b using log-log linear regression.
    Returns (a, b, r2, median_abs_pct_error).
    """
    # Filter valid
    mask = (m2_arr > 0) & (price_arr > 0)
    x = np.log(m2_arr[mask])
    y = np.log(price_arr[mask])
    n = len(x)
    if n < 3:
        return None

    # Linear regression: y = intercept + slope * x
    A = np.vstack([x, np.ones(len(x))]).T
    result = np.linalg.lstsq(A, y, rcond=None)
    slope, intercept = result[0]

    a = np.exp(intercept)
    b = slope

    # R²
    y_pred = intercept + slope * x
    ss_res = np.sum((y - y_pred) ** 2)
    ss_tot = np.sum((y - np.mean(y)) ** 2)
    r2 = 1 - ss_res / ss_tot if ss_tot > 0 else 0

    # Median absolute percentage error
    pred_prices = a * m2_arr[mask] ** b
    pct_errors = np.abs(price_arr[mask] - pred_prices) / price_arr[mask] * 100
    median_ape = np.median(pct_errors)
    mean_ape = np.mean(pct_errors)

    return {
        "a": round(a, 4),
        "b": round(b, 4),
        "n": int(n),
        "r2": round(r2, 4),
        "median_ape": round(median_ape, 1),
        "mean_ape": round(mean_ape, 1),
    }


def main():
    df = pd.read_excel(EXCEL_PATH, header=None, skiprows=7)

    # Extract key columns
    data = pd.DataFrame({
        "name": df[5].astype(str).str.strip(),
        "m2": pd.to_numeric(df[13], errors="coerce"),
        "dguv_price": pd.to_numeric(df[14], errors="coerce"),
        "vds_price": pd.to_numeric(df[15], errors="coerce"),
    })

    # Filter out invalid
    data = data[data["name"].notna() & (data["name"] != "nan")]
    data = data[data["m2"].notna() & (data["m2"] > 0)]
    data = data[data["dguv_price"].notna() & (data["dguv_price"] > 0)]

    print(f"Total valid rows: {len(data)}")
    print()

    # Classify
    data["typ"] = data["name"].apply(classify_building)

    # Show classification summary
    print("=" * 80)
    print("CLASSIFICATION SUMMARY")
    print("=" * 80)
    typ_counts = data["typ"].value_counts().sort_values(ascending=False)
    for typ, count in typ_counts.items():
        print(f"  {typ:25s}: {count:3d} buildings")
    print()

    # Show what's in each category
    print("=" * 80)
    print("BUILDINGS PER CATEGORY")
    print("=" * 80)
    for typ in sorted(data["typ"].unique()):
        subset = data[data["typ"] == typ]
        print(f"\n--- {typ} ({len(subset)} buildings) ---")
        for _, row in subset.iterrows():
            print(f"  {row['name'][:55]:55s}  m²={row['m2']:>8.0f}  DGUV={row['dguv_price']:>10.1f}  VdS={row['vds_price']:>10.1f}")

    # =====================================================
    # DGUV POWER-LAW REGRESSION
    # =====================================================
    print()
    print("=" * 80)
    print("DGUV V3 POWER-LAW REGRESSION: price = a * m²^b")
    print("=" * 80)
    print()

    results_dguv = {}
    MIN_N = 5

    for typ in sorted(data["typ"].unique()):
        subset = data[data["typ"] == typ]
        if len(subset) < MIN_N:
            print(f"  {typ:25s}: SKIP (n={len(subset)} < {MIN_N})")
            continue
        res = fit_power_law(subset["m2"].values, subset["dguv_price"].values)
        if res:
            results_dguv[typ] = res
            print(f"  {typ:25s}: a={res['a']:10.4f}, b={res['b']:.4f}, n={res['n']:3d}, "
                  f"R²={res['r2']:.4f}, MdAPE={res['median_ape']:5.1f}%, MnAPE={res['mean_ape']:5.1f}%")
        else:
            print(f"  {typ:25s}: FIT FAILED (n={len(subset)})")

    # Fit all-buildings fallback
    print()
    res_all = fit_power_law(data["m2"].values, data["dguv_price"].values)
    results_dguv["_all"] = res_all
    print(f"  {'ALL BUILDINGS':25s}: a={res_all['a']:10.4f}, b={res_all['b']:.4f}, n={res_all['n']:3d}, "
          f"R²={res_all['r2']:.4f}, MdAPE={res_all['median_ape']:5.1f}%, MnAPE={res_all['mean_ape']:5.1f}%")

    # =====================================================
    # VdS POWER-LAW REGRESSION
    # =====================================================
    print()
    print("=" * 80)
    print("VdS POWER-LAW REGRESSION: price = a * m²^b")
    print("=" * 80)
    print()

    data_vds = data[data["vds_price"].notna() & (data["vds_price"] > 0)]
    results_vds = {}

    for typ in sorted(data_vds["typ"].unique()):
        subset = data_vds[data_vds["typ"] == typ]
        if len(subset) < MIN_N:
            print(f"  {typ:25s}: SKIP (n={len(subset)} < {MIN_N})")
            continue
        res = fit_power_law(subset["m2"].values, subset["vds_price"].values)
        if res:
            results_vds[typ] = res
            print(f"  {typ:25s}: a={res['a']:10.4f}, b={res['b']:.4f}, n={res['n']:3d}, "
                  f"R²={res['r2']:.4f}, MdAPE={res['median_ape']:5.1f}%, MnAPE={res['mean_ape']:5.1f}%")

    res_all_vds = fit_power_law(data_vds["m2"].values, data_vds["vds_price"].values)
    results_vds["_all"] = res_all_vds
    print(f"\n  {'ALL BUILDINGS':25s}: a={res_all_vds['a']:10.4f}, b={res_all_vds['b']:.4f}, n={res_all_vds['n']:3d}, "
          f"R²={res_all_vds['r2']:.4f}, MdAPE={res_all_vds['median_ape']:5.1f}%, MnAPE={res_all_vds['mean_ape']:5.1f}%")

    # =====================================================
    # VdS/DGUV RATIO ANALYSIS
    # =====================================================
    print()
    print("=" * 80)
    print("VdS/DGUV RATIO PER NUTZUNGSTYP")
    print("=" * 80)
    print()

    data_both = data[(data["vds_price"].notna()) & (data["vds_price"] > 0)].copy()
    data_both["vds_dguv_ratio"] = data_both["vds_price"] / data_both["dguv_price"]

    ratio_results = {}
    for typ in sorted(data_both["typ"].unique()):
        subset = data_both[data_both["typ"] == typ]
        if len(subset) < 3:
            continue
        ratio = subset["vds_dguv_ratio"]
        ratio_results[typ] = {
            "n": len(subset),
            "mean": round(ratio.mean(), 4),
            "median": round(ratio.median(), 4),
            "std": round(ratio.std(), 4),
            "min": round(ratio.min(), 4),
            "max": round(ratio.max(), 4),
        }
        print(f"  {typ:25s}: n={len(subset):3d}, median={ratio.median():.3f}, "
              f"mean={ratio.mean():.3f}, std={ratio.std():.3f}, "
              f"range=[{ratio.min():.3f}, {ratio.max():.3f}]")

    overall_ratio = data_both["vds_dguv_ratio"]
    print(f"\n  {'OVERALL':25s}: n={len(data_both):3d}, median={overall_ratio.median():.3f}, "
          f"mean={overall_ratio.mean():.3f}, std={overall_ratio.std():.3f}")

    # =====================================================
    # VdS/DGUV RATIO BY SIZE BRACKET
    # =====================================================
    print()
    print("=" * 80)
    print("VdS/DGUV RATIO BY SIZE BRACKET (m²)")
    print("=" * 80)
    print()

    brackets = [
        (0, 200, "<200"),
        (200, 500, "200-500"),
        (500, 1000, "500-1k"),
        (1000, 2000, "1k-2k"),
        (2000, 5000, "2k-5k"),
        (5000, 10000, "5k-10k"),
        (10000, 50000, "10k-50k"),
        (50000, 999999, "50k+"),
    ]

    for lo, hi, label in brackets:
        subset = data_both[(data_both["m2"] >= lo) & (data_both["m2"] < hi)]
        if len(subset) == 0:
            continue
        ratio = subset["vds_dguv_ratio"]
        print(f"  {label:10s}: n={len(subset):3d}, median={ratio.median():.3f}, "
              f"mean={ratio.mean():.3f}, range=[{ratio.min():.3f}, {ratio.max():.3f}]")

    # =====================================================
    # OUTPUT: PYTHON DICT FORMAT
    # =====================================================
    print()
    print("=" * 80)
    print("PYTHON DICT — AUGSBURG_DGUV_REGRESSION")
    print("=" * 80)
    print()
    print("AUGSBURG_DGUV_REGRESSION = {")
    for typ in sorted(results_dguv.keys()):
        r = results_dguv[typ]
        print(f'    "{typ}": {{"a": {r["a"]}, "b": {r["b"]}, "n": {r["n"]}, "r2": {r["r2"]}, "median_ape": {r["median_ape"]}}},')
    print("}")

    print()
    print("AUGSBURG_VDS_REGRESSION = {")
    for typ in sorted(results_vds.keys()):
        r = results_vds[typ]
        print(f'    "{typ}": {{"a": {r["a"]}, "b": {r["b"]}, "n": {r["n"]}, "r2": {r["r2"]}, "median_ape": {r["median_ape"]}}},')
    print("}")

    print()
    print("AUGSBURG_VDS_DGUV_RATIO = {")
    for typ in sorted(ratio_results.keys()):
        r = ratio_results[typ]
        print(f'    "{typ}": {{"median": {r["median"]}, "mean": {r["mean"]}, "n": {r["n"]}}},')
    print("}")

    # =====================================================
    # SPOT CHECKS: Show predictions vs actuals for some buildings
    # =====================================================
    print()
    print("=" * 80)
    print("SPOT CHECKS — Predicted vs Actual (DGUV, using per-type model)")
    print("=" * 80)
    print()

    # Pick 20 random buildings
    sample = data.sample(min(30, len(data)), random_state=42)
    for _, row in sample.iterrows():
        typ = row["typ"]
        m2 = row["m2"]
        actual = row["dguv_price"]
        if typ in results_dguv:
            r = results_dguv[typ]
        else:
            r = results_dguv["_all"]
        predicted = r["a"] * m2 ** r["b"]
        pct_err = (predicted - actual) / actual * 100
        model_used = typ if typ in results_dguv else "_all"
        print(f"  {row['name'][:40]:40s} typ={model_used:15s} m²={m2:>8.0f}  "
              f"actual={actual:>9.1f}  pred={predicted:>9.1f}  err={pct_err:>+6.1f}%")


if __name__ == "__main__":
    main()
