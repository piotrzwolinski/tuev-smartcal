"""PV-Anlagen + Ladesäulen Pricing — LPV Abschnitt 4+5.

S. Veit Mail 30.05: "wünschenswert für 08.06, keine komplexe Preislogik"
"""


# ═══════════════════════════════════════════════════════════════
# LADESÄULEN (LPV Abschnitt 5)
# ═══════════════════════════════════════════════════════════════

LADESAEULEN_PREISE = {
    ("wallbox", 1): 71.20,
    ("wallbox", 2): 80.10,
    ("dc", 1): 267.00,
    ("dc", 2): 284.80,
    ("dc", 3): 302.60,
}

LADESAEULEN_WEITERE = {
    ("wallbox", 1): 44.50,
    ("wallbox", 2): 53.40,
    ("dc", 1): 89.00,
    ("dc", 2): 89.00,
    ("dc", 3): 89.00,
}


def ladesaeulen_preis(typ: str, anzahl_anschluesse: int, anzahl_saeulen: int) -> dict:
    """Berechne Ladesäulen-Prüfkosten.

    Args:
        typ: "wallbox" oder "dc" (Schnellladesäule)
        anzahl_anschluesse: 1, 2 oder 3 (pro Säule)
        anzahl_saeulen: Gesamtanzahl Säulen
    """
    key = (typ.lower(), min(anzahl_anschluesse, 3 if typ == "dc" else 2))
    erste = LADESAEULEN_PREISE.get(key)
    weitere_preis = LADESAEULEN_WEITERE.get(key)

    if erste is None:
        return {"error": f"Unbekannter Ladesäulen-Typ: {typ}/{anzahl_anschluesse}"}

    if anzahl_saeulen <= 0:
        return {"preis": 0, "positionen": []}

    weitere = max(0, anzahl_saeulen - 1)
    total = erste + weitere * (weitere_preis or 0)

    return {
        "preis": round(total, 2),
        "positionen": [
            {"name": f"Erste {typ.upper()}-Ladesäule ({anzahl_anschluesse} Anschl.)", "betrag": erste},
            *([{"name": f"{weitere}× weitere Ladesäule(n)", "betrag": round(weitere * weitere_preis, 2)}] if weitere > 0 else []),
        ],
        "_quelle": "LPV Abschnitt 5",
        "_typ": "regel",
    }


# ═══════════════════════════════════════════════════════════════
# PV-ANLAGEN (LPV Abschnitt 4)
# ═══════════════════════════════════════════════════════════════

# 4.1 Ordnungsprüfung nach VdS 2871
PV_VDS_PAUSCHALEN = [
    (30, 200.00),    # 0-30 kWp
    (60, 300.00),    # 30-60 kWp
    (150, 400.00),   # 60-150 kWp
    (999999, 600.00),  # ab 150 kWp
]

# 4.2 Prüfung nach DIN VDE 0126-23-1
PV_DIN_GRUNDPREIS = 540.00
PV_DIN_ZUSCHLAG_30_250 = 6.50   # €/kWp für 30-250 kWp
PV_DIN_ZUSCHLAG_250_2000 = 4.50  # €/kWp für 250-2000 kWp


def pv_preis_vds(kwp: float) -> dict:
    """PV Ordnungsprüfung nach VdS 2871."""
    for grenze, pauschale in PV_VDS_PAUSCHALEN:
        if kwp <= grenze:
            return {
                "preis": pauschale,
                "positionen": [{"name": f"PV Ordnungsprüfung VdS 2871 ({kwp:.0f} kWp)", "betrag": pauschale}],
                "_quelle": "LPV Abschnitt 4.1",
                "_typ": "regel",
            }
    return {"preis": 600.00, "positionen": [{"name": "PV VdS ab 150 kWp", "betrag": 600.00}], "_quelle": "LPV 4.1", "_typ": "regel"}


def pv_preis_din(kwp: float) -> dict:
    """PV Prüfung nach DIN VDE 0126-23-1."""
    total = PV_DIN_GRUNDPREIS

    positionen = [{"name": "PV Grundpreis DIN VDE 0126-23-1", "betrag": PV_DIN_GRUNDPREIS}]

    if kwp > 30:
        kwp_30_250 = min(kwp, 250) - 30
        if kwp_30_250 > 0:
            zuschlag = round(kwp_30_250 * PV_DIN_ZUSCHLAG_30_250, 2)
            total += zuschlag
            positionen.append({"name": f"Zuschlag {kwp_30_250:.0f} kWp × {PV_DIN_ZUSCHLAG_30_250}€", "betrag": zuschlag})

    if kwp > 250:
        kwp_250_2000 = min(kwp, 2000) - 250
        zuschlag = round(kwp_250_2000 * PV_DIN_ZUSCHLAG_250_2000, 2)
        total += zuschlag
        positionen.append({"name": f"Zuschlag {kwp_250_2000:.0f} kWp × {PV_DIN_ZUSCHLAG_250_2000}€", "betrag": zuschlag})

    return {
        "preis": round(total, 2),
        "positionen": positionen,
        "_quelle": "LPV Abschnitt 4.2",
        "_typ": "regel",
    }
