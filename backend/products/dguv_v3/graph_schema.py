"""Load DGUV V3 pricing rules into FalkorDB graph.

All rules from LPV B04 Kap. 2 as graph nodes + relationships.
Formula: 250€ Grundpreis + Fläche × €/10m² per Installationskategorie.

Usage:
    from products.dguv_v3.graph_schema import load_dguv_graph
    stats = load_dguv_graph()
"""

from common.database import get_graph

GRAPH_NAME = "dguv_v3"


def load_dguv_graph() -> dict:
    graph = get_graph(GRAPH_NAME)
    graph.query("MATCH (n) DETACH DELETE n")

    statements = []

    # ── 1. PRODUKT ───────────────────────────────────────────
    statements.append("""
    CREATE (:Produkt {
        id: 'DGUV_V3_ORTSFEST',
        name: 'DGUV V3 ortsfeste elektrische Anlage',
        lpv_referenz: 'B04 Kap. 2',
        grundpreis: 250.00,
        einheit: 'Anlage',
        beschreibung: 'Wiederkehrende Prüfung ortsfester elektrischer Anlagen nach DIN VDE 0105-100/A1 und DGUV Vorschrift 3.'
    })
    """)

    # ── 2. INSTALLATIONSKATEGORIEN ───────────────────────────
    for kid, name, preis, beschreibung in [
        ('KAT_1', 'Bürofläche', 1.00, 'Büro, Verwaltung, Beratung'),
        ('KAT_2', 'Produktionsfläche', 2.00, 'Industrie, Fertigung, Werkstatt'),
        ('KAT_3', 'Lagerfläche', 1.50, 'Lager, Logistik'),
        ('KAT_4', 'Verkehrsfläche', 3.00, 'Flure, Treppenhäuser, Parkflächen'),
        ('KAT_5', 'Sonderfläche', 5.00, 'OP-Saal, Labor, Reinraum, Ex-Bereich'),
    ]:
        statements.append(f"""
        CREATE (:Installationskategorie {{id: '{kid}', name: '{name}', preis_per_10m2: {preis}, beschreibung: '{beschreibung}', quelle: 'LPV B04 Kap. 2'}})
        """)
    statements.append("""
    MATCH (p:Produkt {id: 'DGUV_V3_ORTSFEST'}), (k:Installationskategorie)
    CREATE (p)-[:HAT_KATEGORIE]->(k)
    """)

    # ── 3. VERTEILUNGEN ──────────────────────────────────────
    for vid, name, preis in [
        ('VERT_UV', 'Unterverteilung (UV)', 25.00),
        ('VERT_HV', 'Hauptverteilung (HV)', 85.00),
        ('VERT_NSHV', 'Niederspannungshauptverteilung (NSHV)', 145.00),
    ]:
        statements.append(f"""
        CREATE (:Verteilung {{id: '{vid}', name: '{name}', preis_pro_einheit: {preis}, quelle: 'LPV B04 Kap. 2'}})
        """)
    statements.append("""
    MATCH (p:Produkt {id: 'DGUV_V3_ORTSFEST'}), (v:Verteilung)
    CREATE (p)-[:HAT_VERTEILUNG]->(v)
    """)

    # ── 4. SONDERZUSCHLÄGE (absolute €) ──────────────────────
    statements.append("""
    CREATE (:Sonderzuschlag {id: 'SZ_NEA', name: 'Netzersatzanlage (NEA)', betrag: 320.00, bedingung: 'nea_vorhanden', quelle: 'LPV B04 Kap. 2'})
    """)
    statements.append("""
    CREATE (:Sonderzuschlag {id: 'SZ_SV_NSHV', name: 'Sicherheitsstromversorgung NSHV', betrag: 180.00, bedingung: 'sv_nshv_vorhanden', quelle: 'LPV B04 Kap. 2'})
    """)
    statements.append("""
    MATCH (p:Produkt {id: 'DGUV_V3_ORTSFEST'}), (s:Sonderzuschlag)
    CREATE (p)-[:HAT_SONDERZUSCHLAG]->(s)
    """)

    # ── 5. GRUNDKOSTEN (shared) ──────────────────────────────
    statements.append("""
    CREATE (:Grundkosten {id: 'GRUND_PAUSCHALE', name: 'Pauschale Auftragsanlage', betrag: 256.00, quelle: 'LPV Teil A'})
    """)
    statements.append("""
    CREATE (:Grundkosten {id: 'GRUND_ORDNUNG', name: 'Ordnungsprüfung Dokumente', betrag: 242.00, bedingung: 'nur baurechtlich', quelle: 'LPV Teil A'})
    """)
    statements.append("""
    CREATE (:Grundkosten {id: 'GRUND_PRUEFMITTEL', name: 'Energie-/Prüfmittelpauschale', betrag_pro_tag: 49.00, quelle: 'LPV Teil A §4'})
    """)

    # ── 6. STUNDENSÄTZE ──────────────────────────────────────
    for sid, name, betrag in [
        ('STD_EINFACH', 'Einfache Sachverhalte', 180.00),
        ('STD_SCHWIERIG', 'Schwierige Sachverhalte', 208.00),
        ('STD_KOMPLEX', 'Komplexe Sachverhalte', 239.00),
    ]:
        statements.append(f"""
        CREATE (:Stundensatz {{id: '{sid}', name: '{name}', betrag: {betrag}, quelle: 'LPV Teil A §4.2'}})
        """)

    # ── 7. REISEKOSTEN ───────────────────────────────────────
    statements.append("""
    CREATE (:Reisekostenregel {id: 'RK_PKW', name: 'Kilometergeld PKW', betrag_pro_km: 1.10, quelle: 'LPV Teil A §4.3'})
    """)

    # ── 8. TAGEGELD ──────────────────────────────────────────
    for tid, von, bis, betrag in [
        ('TG_6_8', 6, 8, 6.00),
        ('TG_8_14', 8, 14, 25.00),
        ('TG_14_24', 14, 24, 30.00),
    ]:
        statements.append(f"""
        CREATE (:Tagegeld {{id: '{tid}', von_h: {von}, bis_h: {bis}, betrag: {betrag}, quelle: 'LPV Teil A §4.3'}})
        """)

    # ── 9. BERICHTSTYPEN ─────────────────────────────────────
    for bid, name, betrag in [
        ('BER_KLEIN', 'Kleine Anlagen', 119.00),
        ('BER_STANDARD', 'Standardbericht', 380.00),
        ('BER_KOMPLEX', 'Komplexer Sachverhalt', 550.00),
    ]:
        statements.append(f"""
        CREATE (:Berichtstyp {{id: '{bid}', name: '{name}', betrag: {betrag}, quelle: 'LPV B04'}})
        """)

    # ── 10. ZUSCHLÄGE (prozentual) ───────────────────────────
    for zid, name, prozent, bedingung in [
        ('ZS_NICHT_VEREIN', 'Nicht-Vereinsmitglied', 0.20, 'kein Rahmenvertrag'),
        ('ZS_ERSTPRUEFUNG', 'Erstprüfung', 1.00, 'vor erster Inbetriebnahme'),
        ('ZS_EIL', 'Eilzuschlag', 0.25, 'bevorzugte Bearbeitung'),
    ]:
        statements.append(f"""
        CREATE (:Zuschlag {{id: '{zid}', name: '{name}', prozent: {prozent}, bedingung: '{bedingung}', quelle: 'LPV Teil A'}})
        """)

    # ── 11. GEBÄUDETYPEN + typische Installationskategorie ───
    gebaeudetypen = [
        ('GT_BUERO', 'Bürogebäude', 'KAT_1', 100, 5000),
        ('GT_SERVICE', 'Service Center', 'KAT_1', 200, 3000),
        ('GT_SENIOR', 'Seniorentreff', 'KAT_1', 50, 1000),
        ('GT_HOTEL', 'Hotel', 'KAT_1', 500, 15000),
        ('GT_KRANKENHAUS', 'Krankenhaus', 'KAT_5', 2000, 100000),
        ('GT_INDUSTRIE', 'Industriegebäude', 'KAT_2', 500, 50000),
        ('GT_SCHULE', 'Schule', 'KAT_1', 500, 10000),
        ('GT_VERKAUF', 'Verkaufsstätte', 'KAT_1', 200, 20000),
    ]
    for gtid, name, typ_kat, fl_min, fl_max in gebaeudetypen:
        statements.append(f"""
        CREATE (:Gebaeudetyp {{id: '{gtid}', name: '{name}', typische_flaeche_min: {fl_min}, typische_flaeche_max: {fl_max}}})
        """)
        statements.append(f"""
        MATCH (g:Gebaeudetyp {{id: '{gtid}'}}), (k:Installationskategorie {{id: '{typ_kat}'}})
        CREATE (g)-[:TYPISCHE_KATEGORIE]->(k)
        """)

    # ── 12. STANDORTE (23 TÜV-Niederlassungen) ──────────────
    standorte = [
        ('AUG', 'Augsburg', 48.3543, 10.8735), ('BER', 'Berlin', 52.5785, 13.3195),
        ('DAR', 'Darmstadt', 49.8590, 8.6365), ('DRE', 'Dresden', 51.0580, 13.6940),
        ('ESS', 'Essen', 51.4470, 6.9880), ('FIL', 'Filderstadt', 48.6560, 9.2200),
        ('FRE', 'Freiburg', 48.0200, 7.8340), ('HAM', 'Hamburg', 53.5740, 9.9270),
        ('HAN', 'Hannover', 52.3870, 9.7100), ('HEI', 'Heilbronn', 49.1380, 9.2230),
        ('HOF', 'Hof', 50.3100, 11.9250), ('KAR', 'Karlsruhe', 48.9870, 8.3990),
        ('LEI', 'Leipzig', 51.3680, 12.3410), ('MAN', 'Mannheim', 49.4930, 8.4800),
        ('MUC', 'München', 48.1420, 11.5170), ('NBG', 'Nürnberg', 49.4440, 11.0250),
        ('RAV', 'Ravensburg', 47.7820, 9.6120), ('RGB', 'Regensburg', 49.0100, 12.0840),
        ('ROS', 'Rostock', 54.0810, 12.1070), ('SBR', 'St. Ingbert', 49.2770, 7.1150),
        ('TRT', 'Trostberg', 48.0260, 12.5450), ('ULM', 'Ulm', 48.3780, 9.9590),
        ('WZB', 'Würzburg', 49.7830, 9.9400),
    ]
    for sid, name, lat, lon in standorte:
        statements.append(f"""
        CREATE (:Standort {{id: 'STD_{sid}', name: '{name}', lat: {lat}, lon: {lon}}})
        """)

    # ── 13. PRUEFTAGE ────────────────────────────────────────
    for pid, von, bis, tage in [
        ('PT_1', 1, 500, 0.5),
        ('PT_2', 501, 2000, 1.0),
        ('PT_3', 2001, 5000, 2.0),
        ('PT_4', 5001, 999999, -1),  # formel: flaeche/2500
    ]:
        statements.append(f"""
        CREATE (:Prueftagschaetzung {{id: '{pid}', von_m2: {von}, bis_m2: {bis}, tage: {tage}, formel: '{"flaeche/2500" if tage == -1 else ""}', quelle: 'Heuristik'}})
        """)

    # ── 14. CROSS-SELL ───────────────────────────────────────
    statements.append("""
    CREATE (:CrossSell {id: 'CS_BLITZ', empfehlung: 'Blitzschutzprüfung — Kombi-Begehung spart Reisekosten', produkt: 'blitzschutz', prioritaet: 'hoch'})
    """)
    statements.append("""
    CREATE (:CrossSell {id: 'CS_RLT', empfehlung: 'RLT-Hygieneinspektion (VDI 6022) — gleiche Begehung möglich', produkt: 'rlt', prioritaet: 'mittel'})
    """)

    # Execute all
    for stmt in statements:
        try:
            graph.query(stmt.strip())
        except Exception as e:
            print(f"ERROR: {e}\n  Statement: {stmt.strip()[:100]}")

    nodes = graph.query("MATCH (n) RETURN count(n) AS cnt").result_set[0][0]
    edges = graph.query("MATCH ()-[r]->() RETURN count(r) AS cnt").result_set[0][0]
    labels = graph.query("MATCH (n) RETURN DISTINCT labels(n)[0] AS l, count(n) AS c ORDER BY c DESC")

    return {
        "graph": GRAPH_NAME,
        "nodes": nodes,
        "edges": edges,
        "labels": {row[0]: row[1] for row in labels.result_set},
    }
