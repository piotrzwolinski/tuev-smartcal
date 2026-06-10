"""DGUV V3 ortsfeste elektrische Anlage pricing rules.

PRD v2.1 — Graph-as-Single-Source-of-Truth with Python fallback.
All values read from FalkorDB graph first. Python dicts = fallback only.
"""

from products.dguv_v3.merkmale import (
    DGUVMerkmale,
    GebaeudeNutzungDGUV,
    Installationskategorie,
    Reifegrad,
    NutzungsMixEintrag,
)
from common.pricing_primitives import (
    ZUSCHLAG_NICHT_VEREINSMITGLIED,
    ZUSCHLAG_EILZUSCHLAG,
    ZUSCHLAG_ERSTPRUEFUNG,
)
from common.graph_reader import get_reader


DGUV_GRUNDPREIS_ANLAGE = 250.00
VDS_GRUNDPREIS_ANLAGE = 250.00
VDS_ID_PAUSCHALE = 208.00  # VdS: ID=208€, DGUV: ID=180€
DGUV_VDS_SYNERGIE_ZUSCHLAG = 0.50  # S. Pausch: "DGUV+VdS gemeinsam = +50% auf VdS-Preis"

# Kalkulationshilfen NBG / Hilfstabellen / 2026
# _quelle: 'Kalkulationshilfen NBG', _typ: 'regel'
PREIS_PER_10M2 = {
    Installationskategorie.KAT_1: 1.00,   # Wohnung, Freiflächen
    Installationskategorie.KAT_2: 3.10,   # Büro, Schule, Restaurant, Lager
    Installationskategorie.KAT_3: 5.00,   # Supermarkt, Produktion, Museum
    Installationskategorie.KAT_4: 5.40,   # Technikräume, Reinraum
    Installationskategorie.KAT_5: 5.40,   # Sonder (OP, Labor) — same as Kat4 until clarified
    Installationskategorie.KAT_6: 6.00,   # NSHV, Trafo — S. Veit Mail, Preis TBD → 6.00 estimate
}

DEGRESSION_DGUV = [(0, 0.80), (2000, 0.80), (4000, 0.60), (6000, 0.50), (10000, 0.40), (25000, 0.30)]
DEGRESSION_VDS = [(0, 1.00), (2000, 0.90), (4000, 0.80), (6000, 0.70), (10000, 0.50), (25000, 0.35)]

KLEINAUFTRAG_MAX_VERT = 2
KLEINAUFTRAG_MAX_FLAECHE = 300
KLEINAUFTRAG_STUNDENSATZ = 180.00
KLEINAUFTRAG_STUNDEN_PRO_KOMPONENTE = 1.5
KLEINAUFTRAG_MIN_PAUSCHALE = 270.00
KLEINAUFTRAG_GRUNDKOSTEN_REDUZIERT = 100.00

REFERENZ_BLEND_GEWICHT = 0.40
REFERENZ_BLEND_CAP = 0.30
REFERENZ_BLEND_MAX_ALTER = 3

ZUSCHLAG_NEA = 320.00
ZUSCHLAG_SV_NSHV = 180.00

PREIS_VERTEILUNG_UV = 25.00
PREIS_VERTEILUNG_HV = 85.00
PREIS_VERTEILUNG_NSHV = 145.00

# S. Veit Mail 30.05 Punkt 7
# _quelle: 'S. Veit Mail 30.05', _typ: 'fachexperte'
REIFEGRAD_FAKTOR = {
    Reifegrad.RG_1: 1.25,
    Reifegrad.RG_2: 1.25,
    Reifegrad.RG_3: 1.00,
    Reifegrad.RG_4: 0.80,
}

# S. Pausch Mail 29.05 + S. Veit Mail 30.05 Punkt 6
VOLLERFASSUNG_FAKTOR = 1.30

# S. Veit Mail 30.05 Punkt 9
PREISSTEIGERUNG = {
    2020: 0.282,
    2021: 0.244,
    2022: 0.208,
    2023: 0.148,
    2024: 0.083,
    2025: 0.055,
    2026: 0.000,
}
REFERENZPREIS_WARN_SCHWELLE = 0.20

# Kalkulationshilfen NBG / Hilfstabellen — Nutzung→Kategorie
NUTZUNG_ZU_KATEGORIE = {
    "wohnung": Installationskategorie.KAT_1,
    "freiflaeche": Installationskategorie.KAT_1,
    "allgemeinbereich": Installationskategorie.KAT_1,
    "buero": Installationskategorie.KAT_2,
    "schule": Installationskategorie.KAT_2,
    "restaurant": Installationskategorie.KAT_2,
    "lager": Installationskategorie.KAT_2,
    "logistik": Installationskategorie.KAT_2,
    "krankenhaus": Installationskategorie.KAT_2,
    "altenheim": Installationskategorie.KAT_2,
    "werkstatt": Installationskategorie.KAT_2,
    "hotel": Installationskategorie.KAT_2,
    "labor": Installationskategorie.KAT_2,
    "archiv": Installationskategorie.KAT_2,
    "verwaltung": Installationskategorie.KAT_2,
    "kueche": Installationskategorie.KAT_3,
    "kantine": Installationskategorie.KAT_3,
    "konferenz": Installationskategorie.KAT_3,
    "konferenzraum": Installationskategorie.KAT_3,
    "konferenzsaal": Installationskategorie.KAT_3,
    "supermarkt": Installationskategorie.KAT_3,
    "produktion": Installationskategorie.KAT_3,
    "museum": Installationskategorie.KAT_3,
    "edv": Installationskategorie.KAT_3,
    "versammlungsraum": Installationskategorie.KAT_3,
    "verkaufsflaeche": Installationskategorie.KAT_3,
    "druckerei": Installationskategorie.KAT_3,
    "technikraum": Installationskategorie.KAT_4,
    "reinraum": Installationskategorie.KAT_4,
    "op": Installationskategorie.KAT_5,
    "nshv": Installationskategorie.KAT_6,
    "trafo": Installationskategorie.KAT_6,
    "batterieladestation": Installationskategorie.KAT_6,
}

TYPICAL_KAT = {
    GebaeudeNutzungDGUV.BUEROGEBAEUDE: Installationskategorie.KAT_2,
    GebaeudeNutzungDGUV.SERVICE_CENTER: Installationskategorie.KAT_2,
    GebaeudeNutzungDGUV.SENIORENTREFF: Installationskategorie.KAT_2,
    GebaeudeNutzungDGUV.HOTEL: Installationskategorie.KAT_2,
    GebaeudeNutzungDGUV.INDUSTRIE: Installationskategorie.KAT_3,
    GebaeudeNutzungDGUV.SCHULE: Installationskategorie.KAT_2,
    GebaeudeNutzungDGUV.VERKAUFSSTAETTE: Installationskategorie.KAT_3,
    GebaeudeNutzungDGUV.KRANKENHAUS: Installationskategorie.KAT_2,
    GebaeudeNutzungDGUV.TIEFGARAGE: Installationskategorie.KAT_1,
    GebaeudeNutzungDGUV.VERSAMMLUNGSSTAETTE: Installationskategorie.KAT_3,
    GebaeudeNutzungDGUV.MOEBELHAUS: Installationskategorie.KAT_3,
    GebaeudeNutzungDGUV.GARTENMARKT: Installationskategorie.KAT_3,
}

TYPICAL_FLAECHE = {
    GebaeudeNutzungDGUV.BUEROGEBAEUDE: (100, 5000),
    GebaeudeNutzungDGUV.SERVICE_CENTER: (200, 3000),
    GebaeudeNutzungDGUV.SENIORENTREFF: (50, 1000),
    GebaeudeNutzungDGUV.HOTEL: (500, 15000),
    GebaeudeNutzungDGUV.KRANKENHAUS: (2000, 100000),
    GebaeudeNutzungDGUV.INDUSTRIE: (500, 50000),
    GebaeudeNutzungDGUV.SCHULE: (500, 10000),
    GebaeudeNutzungDGUV.VERKAUFSSTAETTE: (200, 20000),
    GebaeudeNutzungDGUV.TIEFGARAGE: (200, 20000),
    GebaeudeNutzungDGUV.VERSAMMLUNGSSTAETTE: (200, 30000),
    GebaeudeNutzungDGUV.MOEBELHAUS: (500, 30000),
    GebaeudeNutzungDGUV.GARTENMARKT: (500, 20000),
    GebaeudeNutzungDGUV.SONSTIGE: (50, 50000),
}

# Kundenmerkmal → m² Umrechnung
# _quelle: 'Branchenwissen', _typ: 'llm_augmentiert'
UMRECHNUNG_M2 = {
    "zimmer": 30.0,
    "betten": 50.0,
    "klassenraeume": 70.0,
    "stellplaetze": 25.0,
    "mitarbeiter": 15.0,
    "sitzplaetze": 3.0,
}

UMRECHNUNG_PLAUSIBILITAET = {
    GebaeudeNutzungDGUV.HOTEL: (500, 50000),
    GebaeudeNutzungDGUV.KRANKENHAUS: (2000, 200000),
    GebaeudeNutzungDGUV.SCHULE: (500, 30000),
    GebaeudeNutzungDGUV.BUEROGEBAEUDE: (100, 100000),
    GebaeudeNutzungDGUV.TIEFGARAGE: (200, 50000),
    GebaeudeNutzungDGUV.VERSAMMLUNGSSTAETTE: (100, 100000),
}


# ═══════════════════════════════════════════════════════════════
# GRAPH-FIRST READERS (fallback to Python dicts above)
# ═══════════════════════════════════════════════════════════════

def _g_kat_preis(kat: Installationskategorie) -> float:
    r = get_reader()
    return r.get(
        "MATCH (k:Installationskategorie {id: $kid}) RETURN k.preis_per_10m2",
        {"kid": f"KAT_{kat.value}"},
        fallback=PREIS_PER_10M2.get(kat, 3.10),
        cache_key=f"kat_{kat.value}",
    )

def _g_reifegrad(rg: Reifegrad) -> float:
    r = get_reader()
    return r.get(
        "MATCH (r:Reifegrad {id: $rid}) RETURN r.faktor",
        {"rid": f"RG_{rg.value}"},
        fallback=REIFEGRAD_FAKTOR.get(rg, 1.0),
        cache_key=f"rg_{rg.value}",
    )

def _g_vollerfassung() -> float:
    r = get_reader()
    return r.get(
        "MATCH (d:Dokumentationszuschlag {id: 'DOK_VOLL'}) RETURN d.faktor",
        fallback=VOLLERFASSUNG_FAKTOR,
        cache_key="vollerfassung",
    )

def _g_steigerung(jahr: int) -> float | None:
    r = get_reader()
    val = r.get(
        "MATCH (p:Preissteigerung {jahr: $j}) RETURN p.steigerung_vs_2026",
        {"j": jahr},
        fallback=PREISSTEIGERUNG.get(jahr),
        cache_key=f"steig_{jahr}",
    )
    return val

def _g_warn_schwelle() -> float:
    r = get_reader()
    return r.get(
        "MATCH (w:Warnregel {id: 'WARN_REFERENZ'}) RETURN w.schwelle_prozent",
        fallback=REFERENZPREIS_WARN_SCHWELLE * 100,
        cache_key="warn_schwelle",
    ) / 100.0

def _g_typical_kat(nutzung: GebaeudeNutzungDGUV) -> Installationskategorie:
    r = get_reader()
    gt_map = {
        GebaeudeNutzungDGUV.BUEROGEBAEUDE: "GT_BUERO", GebaeudeNutzungDGUV.SCHULE: "GT_SCHULE",
        GebaeudeNutzungDGUV.HOTEL: "GT_HOTEL", GebaeudeNutzungDGUV.KRANKENHAUS: "GT_KRANKENHAUS",
        GebaeudeNutzungDGUV.INDUSTRIE: "GT_INDUSTRIE", GebaeudeNutzungDGUV.VERKAUFSSTAETTE: "GT_VERKAUF",
        GebaeudeNutzungDGUV.TIEFGARAGE: "GT_TIEFGARAGE", GebaeudeNutzungDGUV.VERSAMMLUNGSSTAETTE: "GT_VERSAMMLUNG",
        GebaeudeNutzungDGUV.MOEBELHAUS: "GT_MOEBEL", GebaeudeNutzungDGUV.GARTENMARKT: "GT_GARTEN",
        GebaeudeNutzungDGUV.SERVICE_CENTER: "GT_SERVICE", GebaeudeNutzungDGUV.SENIORENTREFF: "GT_SENIOR",
    }
    gid = gt_map.get(nutzung)
    if not gid:
        return TYPICAL_KAT.get(nutzung, Installationskategorie.KAT_2)
    kid = r.get(
        "MATCH (g:Gebaeudetyp {id: $gid})-[:TYPISCHE_KATEGORIE]->(k) RETURN k.id",
        {"gid": gid},
        fallback=None,
        cache_key=f"typkat_{nutzung.value}",
    )
    if kid:
        num = int(kid.split("_")[1])
        return Installationskategorie(num)
    return TYPICAL_KAT.get(nutzung, Installationskategorie.KAT_2)

def _g_typical_flaeche(nutzung: GebaeudeNutzungDGUV) -> tuple[float, float]:
    r = get_reader()
    gt_map = {
        GebaeudeNutzungDGUV.BUEROGEBAEUDE: "GT_BUERO", GebaeudeNutzungDGUV.SCHULE: "GT_SCHULE",
        GebaeudeNutzungDGUV.HOTEL: "GT_HOTEL", GebaeudeNutzungDGUV.KRANKENHAUS: "GT_KRANKENHAUS",
        GebaeudeNutzungDGUV.INDUSTRIE: "GT_INDUSTRIE", GebaeudeNutzungDGUV.VERKAUFSSTAETTE: "GT_VERKAUF",
        GebaeudeNutzungDGUV.TIEFGARAGE: "GT_TIEFGARAGE",
    }
    gid = gt_map.get(nutzung)
    if gid:
        row = r.get_row(
            "MATCH (g:Gebaeudetyp {id: $gid}) RETURN g.typische_flaeche_min, g.typische_flaeche_max",
            {"gid": gid},
            cache_key=f"flaeche_{nutzung.value}",
        )
        if row and row[0] is not None:
            return (float(row[0]), float(row[1]))
    return TYPICAL_FLAECHE.get(nutzung, (50, 50000))

def _g_mix_kategorie(nutzung_name: str) -> Installationskategorie:
    r = get_reader()
    kid = r.get(
        "MATCH (nm:NutzungsMapping) WHERE toLower(nm.nutzung) = $n RETURN nm.kategorie",
        {"n": nutzung_name.lower().strip()},
        fallback=None,
    )
    if kid:
        num = int(kid.split("_")[1])
        return Installationskategorie(num)
    return NUTZUNG_ZU_KATEGORIE.get(nutzung_name.lower().strip(), Installationskategorie.KAT_2)

def _g_umrechnung(merkmal: str) -> float | None:
    r = get_reader()
    val = r.get(
        "MATCH (ur:Umrechnungsregel {kundenmerkmal: $m}) RETURN ur.faktor_m2",
        {"m": merkmal},
        fallback=UMRECHNUNG_M2.get(merkmal.lower()),
        cache_key=f"umr_{merkmal}",
    )
    return val


def _flaeche(m: DGUVMerkmale) -> float:
    """None-Guard (Plan v2, Phase 0.4): gesamtflaeche_m2 ist Optional — None → 0."""
    return m.gesamtflaeche_m2 or 0.0


def flaechenkosten_degressiv(
    flaeche_m2: float,
    rate_per_10m2: float,
    kurve: list[tuple[float, float]],
) -> float:
    """Bandwise degression on area cost (NBG Kalkulationshilfen).

    Each (ab_m2, faktor) entry defines the factor from ab_m2 onwards.
    Returns total € for the area portion of Prüfkosten.
    """
    total = 0.0
    for i, (ab_m2, faktor) in enumerate(kurve):
        if flaeche_m2 <= ab_m2:
            break
        band_end = kurve[i + 1][0] if i + 1 < len(kurve) else flaeche_m2
        band_m2 = min(flaeche_m2, band_end) - ab_m2
        total += (band_m2 / 10.0) * rate_per_10m2 * faktor
    return round(total, 2)


def _g_degression_kurve(kurve_name: str) -> list[tuple[float, float]]:
    r = get_reader()
    rows = r.get_all(
        "MATCH (f:Flaechenstaffel {kurve: $k}) RETURN f.ab_m2, f.faktor ORDER BY f.ab_m2",
        {"k": kurve_name},
    )
    if rows:
        return [(float(row[0]), float(row[1])) for row in rows]
    fallback = {"dguv": DEGRESSION_DGUV, "vds": DEGRESSION_VDS}
    return fallback.get(kurve_name, DEGRESSION_DGUV)


def resolve_mix_kategorie(nutzung_name: str) -> Installationskategorie:
    return _g_mix_kategorie(nutzung_name)


def auto_correct_kategorie(nutzung: GebaeudeNutzungDGUV) -> Installationskategorie:
    """Return typical Kategorie for a Nutzung from graph. Used by chat coordinator."""
    return _g_typical_kat(nutzung)


def dguv_pruefkosten(m: DGUVMerkmale) -> float:
    """Prüfkosten: Fläche×Kat (ggf. Mix) + Verteilungen + Sonderzuschläge."""
    cost = DGUV_GRUNDPREIS_ANLAGE

    flaeche = _flaeche(m)
    kurve = _g_degression_kurve("dguv")
    if m.nutzungs_mix:
        for eintrag in m.nutzungs_mix:
            kat = eintrag.kategorie or resolve_mix_kategorie(eintrag.nutzung)
            rate = _g_kat_preis(kat)
            cost += flaechenkosten_degressiv(flaeche * eintrag.anteil, rate, kurve)
    else:
        rate = _g_kat_preis(m.primary_installationskategorie)
        cost += flaechenkosten_degressiv(flaeche, rate, kurve)

    cost += m.anzahl_verteilungen_uv * PREIS_VERTEILUNG_UV
    cost += m.anzahl_verteilungen_hv * PREIS_VERTEILUNG_HV
    cost += m.anzahl_verteilungen_nshv * PREIS_VERTEILUNG_NSHV

    if m.nea_vorhanden:
        cost += ZUSCHLAG_NEA
    if m.sv_nshv_vorhanden:
        cost += ZUSCHLAG_SV_NSHV

    cost *= _g_reifegrad(m.reifegrad)

    if m.vollerfassung:
        cost *= _g_vollerfassung()

    return round(cost, 2)


def dguv_estimate_pruef_tage(m: DGUVMerkmale) -> float:
    from products.dguv_v3.merkmale import Pruefart
    if getattr(m, "pruefart", None) == Pruefart.DGUV_ORTSVERAENDERLICH:
        n = m.anzahl_betriebsmittel or 0
        return max(0.5, n / 200)
    flaeche = _flaeche(m)
    if flaeche <= 500:
        return 0.5
    if flaeche <= 2000:
        return 1.0
    if flaeche <= 5000:
        return 2.0
    return max(2.0, flaeche / 2500)


def dguv_choose_bericht_typ(m: DGUVMerkmale) -> str:
    from products.dguv_v3.merkmale import Pruefart
    if getattr(m, "pruefart", None) == Pruefart.DGUV_ORTSVERAENDERLICH:
        return "inklusive"
    flaeche = _flaeche(m)
    total_verteilungen = (
        m.anzahl_verteilungen_uv + m.anzahl_verteilungen_hv + m.anzahl_verteilungen_nshv
    )
    if flaeche <= 500 and total_verteilungen <= 3:
        return "klein"
    if flaeche <= 5000 and total_verteilungen <= 15:
        return "standard"
    return "komplex"


def dguv_zuschlaege(m: DGUVMerkmale) -> list[tuple[str, float]]:
    z = []
    if not m.vereinsmitglied:
        z.append(("Nicht-Vereinsmitglied", ZUSCHLAG_NICHT_VEREINSMITGLIED))
    if m.eilzuschlag:
        z.append(("Eilzuschlag / Sondertermin", ZUSCHLAG_EILZUSCHLAG))
    if m.erstpruefung:
        z.append(("Erstprüfung", ZUSCHLAG_ERSTPRUEFUNG))
    return z


def dguv_referenzpreis(m: DGUVMerkmale) -> dict | None:
    """Referenzpreis-Logik: alter Preis × Steigerung → Vergleich."""
    if m.referenzpreis_jahr is None or m.referenzpreis_betrag is None:
        return None

    steigerung = _g_steigerung(m.referenzpreis_jahr)
    if steigerung is None:
        return {
            "fehler": f"Keine Steigerungsdaten für Jahr {m.referenzpreis_jahr} (nur 2020-2026)",
        }

    fortgeschrieben = round(m.referenzpreis_betrag * (1 + steigerung), 2)
    return {
        "original_jahr": m.referenzpreis_jahr,
        "original_betrag": m.referenzpreis_betrag,
        "steigerung_prozent": steigerung * 100,
        "fortgeschrieben_2026": fortgeschrieben,
    }


def dguv_referenzpreis_vergleich(neukalkulation: float, referenz: dict | None) -> dict | None:
    if referenz is None or "fehler" in referenz:
        return referenz

    fortgeschrieben = referenz["fortgeschrieben_2026"]
    if fortgeschrieben == 0:
        return referenz

    abweichung = (neukalkulation - fortgeschrieben) / fortgeschrieben
    warnung = abs(abweichung) > _g_warn_schwelle()

    return {
        **referenz,
        "neukalkulation": round(neukalkulation, 2),
        "abweichung_prozent": round(abweichung * 100, 1),
        "warnung": warnung,
        "warnung_text": (
            f"Neukalkulation weicht {abweichung*100:+.0f}% vom fortgeschriebenen "
            f"Referenzpreis ({fortgeschrieben:.2f}€) ab — fachliche Plausibilisierung empfohlen."
            if warnung else None
        ),
    }


def vds_pruefkosten(m: DGUVMerkmale) -> float:
    """VdS 2871 Prüfkosten: Grundpreis + Fläche×Kat (VdS-Kurve) + Verteilungen + Sonderzuschläge."""
    cost = VDS_GRUNDPREIS_ANLAGE
    flaeche = _flaeche(m)
    kurve = _g_degression_kurve("vds")

    if m.nutzungs_mix:
        for eintrag in m.nutzungs_mix:
            kat = eintrag.kategorie or resolve_mix_kategorie(eintrag.nutzung)
            rate = _g_kat_preis(kat)
            cost += flaechenkosten_degressiv(flaeche * eintrag.anteil, rate, kurve)
    else:
        rate = _g_kat_preis(m.primary_installationskategorie)
        cost += flaechenkosten_degressiv(flaeche, rate, kurve)

    cost += m.anzahl_verteilungen_uv * PREIS_VERTEILUNG_UV
    cost += m.anzahl_verteilungen_hv * PREIS_VERTEILUNG_HV
    cost += m.anzahl_verteilungen_nshv * PREIS_VERTEILUNG_NSHV

    if m.nea_vorhanden:
        cost += ZUSCHLAG_NEA
    if m.sv_nshv_vorhanden:
        cost += ZUSCHLAG_SV_NSHV

    cost *= _g_reifegrad(m.reifegrad)
    if m.vollerfassung:
        cost *= _g_vollerfassung()

    return round(cost, 2)


def dguv_plus_vds_pruefkosten(m: DGUVMerkmale) -> float:
    """DGUV + VdS gemeinsam: VdS-Preis × 1.5 (S. Pausch Mail 29.05)."""
    vds = vds_pruefkosten(m)
    return round(vds * (1 + DGUV_VDS_SYNERGIE_ZUSCHLAG), 2)


BM_GRUNDPAUSCHALE = 200.00
BM_SATZ_PRO_BM = 9.50
BM_STAFFEL_AB = 500
BM_STAFFEL_FAKTOR = 1.00


def _g_bm_params() -> tuple[float, float, int, float]:
    r = get_reader()
    row = r.get_row(
        "MATCH (b:BMPreis {id: 'BM_SATZ'}) RETURN b.grundpauschale, b.satz_pro_bm, b.staffel_ab_bm, b.staffel_faktor",
        cache_key="bm_params",
    )
    if row and row[0] is not None:
        return (float(row[0]), float(row[1]), int(row[2]), float(row[3]))
    return (BM_GRUNDPAUSCHALE, BM_SATZ_PRO_BM, BM_STAFFEL_AB, BM_STAFFEL_FAKTOR)


def bm_pruefkosten(m: DGUVMerkmale) -> float:
    """MA560 ortsveränderlich: Grundpauschale + n × Satz (all-inclusive, Grund+Bericht=0)."""
    n = m.anzahl_betriebsmittel or 0
    pauschale, satz, staffel_ab, staffel_f = _g_bm_params()
    cost = pauschale + n * satz
    if n > staffel_ab and staffel_f != 1.0:
        over = n - staffel_ab
        cost = pauschale + staffel_ab * satz + over * satz * staffel_f
    return round(cost, 2)


def _g_kleinauftrag_params() -> dict:
    r = get_reader()
    row = r.get_row(
        "MATCH (k:Kleinauftrag {id: 'KLEINAUFTRAG'}) RETURN k.max_verteilungen, k.max_flaeche_m2, k.stundensatz, k.stunden_pro_komponente, k.min_pauschale, k.grundkosten_reduziert",
        cache_key="kleinauftrag",
    )
    if row and row[0] is not None:
        return {"max_vert": int(row[0]), "max_flaeche": float(row[1]), "stundensatz": float(row[2]),
                "stunden_pro_k": float(row[3]), "min_pauschale": float(row[4]), "grundkosten_red": float(row[5])}
    return {"max_vert": KLEINAUFTRAG_MAX_VERT, "max_flaeche": KLEINAUFTRAG_MAX_FLAECHE,
            "stundensatz": KLEINAUFTRAG_STUNDENSATZ, "stunden_pro_k": KLEINAUFTRAG_STUNDEN_PRO_KOMPONENTE,
            "min_pauschale": KLEINAUFTRAG_MIN_PAUSCHALE, "grundkosten_red": KLEINAUFTRAG_GRUNDKOSTEN_REDUZIERT}


def is_kleinauftrag(m: DGUVMerkmale) -> bool:
    p = _g_kleinauftrag_params()
    total_vert = m.anzahl_verteilungen_uv + m.anzahl_verteilungen_hv + m.anzahl_verteilungen_nshv
    flaeche = _flaeche(m)
    return total_vert <= p["max_vert"] and flaeche <= p["max_flaeche"]


def kleinauftrag_pruefkosten(m: DGUVMerkmale) -> float:
    p = _g_kleinauftrag_params()
    total_vert = m.anzahl_verteilungen_uv + m.anzahl_verteilungen_hv + m.anzahl_verteilungen_nshv
    komponenten = max(1, total_vert)
    stunden = p["stunden_pro_k"] * komponenten
    return round(max(p["min_pauschale"], stunden * p["stundensatz"]), 2)


def kleinauftrag_grundkosten(m: DGUVMerkmale) -> float:
    p = _g_kleinauftrag_params()
    return p["grundkosten_red"]


def referenz_blend(neukalkulation: float, m: DGUVMerkmale) -> dict | None:
    """Visible Referenzpreis-Blend: separate Breakdown-Zeile, capped ±30%."""
    if m.referenzpreis_jahr is None or m.referenzpreis_betrag is None:
        return None
    if not getattr(m, "referenz_vergleichbar", False):
        return None

    steigerung = _g_steigerung(m.referenzpreis_jahr)
    if steigerung is None:
        return None

    fortgeschrieben = m.referenzpreis_betrag * (1 + steigerung)
    alter = 2026 - m.referenzpreis_jahr
    if alter > REFERENZ_BLEND_MAX_ALTER:
        gewicht = max(0.1, REFERENZ_BLEND_GEWICHT * (REFERENZ_BLEND_MAX_ALTER / alter))
    else:
        gewicht = REFERENZ_BLEND_GEWICHT

    diff = fortgeschrieben - neukalkulation
    cap = neukalkulation * REFERENZ_BLEND_CAP
    anpassung = max(-cap, min(cap, diff * gewicht))

    return {
        "fortgeschrieben": round(fortgeschrieben, 2),
        "gewicht": round(gewicht, 2),
        "anpassung": round(anpassung, 2),
        "neues_total": round(neukalkulation + anpassung, 2),
    }


def dispatch_pruefkosten(m: DGUVMerkmale) -> float:
    """Route Prüfkosten by Pruefart, with Kleinauftrag override."""
    from products.dguv_v3.merkmale import Pruefart
    pa = getattr(m, "pruefart", Pruefart.DGUV_ORTSFEST)
    if pa == Pruefart.VDS:
        return vds_pruefkosten(m)
    if pa == Pruefart.DGUV_PLUS_VDS:
        return dguv_plus_vds_pruefkosten(m)
    if pa == Pruefart.DGUV_ORTSVERAENDERLICH:
        return bm_pruefkosten(m)
    if is_kleinauftrag(m):
        return kleinauftrag_pruefkosten(m)
    return dguv_pruefkosten(m)


def dguv_validate_ranges(m: DGUVMerkmale) -> tuple[float, str]:
    reasons = []
    confidence = 1.0

    lo, hi = _g_typical_flaeche(m.nutzung)
    if m.gesamtflaeche_m2 is None:
        confidence *= 0.85
        reasons.append(
            "Keine Gesamtfläche angegeben — Kalkulation über alternative Mengen-Inputs"
        )
    elif m.gesamtflaeche_m2 < lo:
        confidence *= 0.85
        reasons.append(
            f"Gesamtfläche ({m.gesamtflaeche_m2:.0f} m²) unter typisch "
            f"für {m.nutzung.value} ({lo}-{hi} m²)"
        )
    elif m.gesamtflaeche_m2 > hi * 1.5:
        confidence *= 0.75
        reasons.append(
            f"Gesamtfläche ({m.gesamtflaeche_m2:.0f} m²) deutlich über typisch "
            f"für {m.nutzung.value} ({lo}-{hi} m²)"
        )

    typical_kat = _g_typical_kat(m.nutzung)
    if typical_kat and m.primary_installationskategorie != typical_kat and not m.nutzungs_mix:
        confidence *= 0.9
        reasons.append(
            f"Installationskategorie {m.primary_installationskategorie.value} "
            f"untypisch für {m.nutzung.value} (typisch Kat {typical_kat.value})"
        )

    total_vert = m.anzahl_verteilungen_uv + m.anzahl_verteilungen_hv + m.anzahl_verteilungen_nshv
    if total_vert == 0:
        confidence *= 0.9
        reasons.append("Keine Verteilungen angegeben — optional zur Verfeinerung")

    if m.reifegrad != Reifegrad.RG_3:
        confidence *= 1.03

    if m.vollerfassung:
        confidence *= 1.02

    if m.referenzpreis_jahr is not None and m.referenzpreis_betrag is not None:
        confidence *= 1.03

    if m.nutzungs_mix:
        confidence *= 1.05

    confidence = min(confidence, 1.0)

    reason = " · ".join(reasons) if reasons else "Alle Merkmale in typischen Bereichen"
    return round(confidence, 2), reason
