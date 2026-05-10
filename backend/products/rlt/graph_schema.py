"""Load RLT pricing rules into FalkorDB graph.

All rules from LPV B05 Kap. 2 as graph nodes + relationships.
2 sub-products: HYG (VDI 6022) + GARAGE (GaStellV/BayBO).

Usage:
    from products.rlt.graph_schema import load_rlt_graph
    stats = load_rlt_graph()
"""

from common.database import get_graph

GRAPH_NAME = "rlt"


def load_rlt_graph() -> dict:
    graph = get_graph(GRAPH_NAME)
    graph.query("MATCH (n) DETACH DELETE n")

    statements = []

    # ── 1. PRODUKTE ──────────────────────────────────────────
    statements.append("""
    CREATE (:Produkt {
        id: 'RLT_HYG',
        name: 'Hygieneinspektion RLT-Anlage (VDI 6022)',
        lpv_referenz: 'B05 Kap. 2.7',
        stundensatz: 208.00,
        stunden_pro_bereich: 2.5,
        labor_pauschale: 180.00,
        beschreibung: 'Hygieneinspektion nach VDI 6022 Blatt 1 — Abklatschproben, Luftkeimmessungen, Sichtprüfung RLT-Gerät und Kanalnetz.'
    })
    """)
    statements.append("""
    CREATE (:Produkt {
        id: 'RLT_GARAGE',
        name: 'Prüfung Garagenlüftung (Baurecht)',
        lpv_referenz: 'B05 Kap. 2.2',
        verrechnung: 'grundpreis_stellplaetze',
        beschreibung: 'Wiederkehrende Prüfung Baurecht — Garagenlüftung nach BayBO, GaStellV, VDI 2053. Volumenstrom, BSK, CO-Warnanlagen.'
    })
    """)
    statements.append("""
    CREATE (:Produkt {
        id: 'RLT_STANDARD',
        name: 'RLT-Anlage allgemein (WPBA)',
        lpv_referenz: 'B05 Kap. 2.1',
        verrechnung: 'grundpreis_volumenstrom',
        beschreibung: 'Wiederkehrende Prüfung Baurecht — Standard-RLT Entrauchung, Druckbelüftung.'
    })
    """)

    # ── 2. GRUNDPREISE GARAGE (Stellplatz-Staffeln) ──────────
    for gid, name, von, bis, preis in [
        ('GP_GARAGE_KLEIN', 'Kleingarage', 1, 30, 450.00),
        ('GP_GARAGE_MITTEL', 'Mittelgarage', 31, 100, 690.00),
        ('GP_GARAGE_GROSS', 'Großgarage', 101, 9999, 1250.00),
    ]:
        statements.append(f"""
        CREATE (:Grundpreis {{id: '{gid}', name: '{name}', von_stellplaetze: {von}, bis_stellplaetze: {bis}, betrag: {preis}, quelle: 'LPV B05 Kap. 2.2'}})
        """)
    statements.append("""
    MATCH (p:Produkt {id: 'RLT_GARAGE'}), (g:Grundpreis)
    WHERE g.id STARTS WITH 'GP_GARAGE'
    CREATE (p)-[:HAT_GRUNDPREIS]->(g)
    """)

    # ── 3. GRUNDPREISE STANDARD RLT (Volumenstrom-Staffeln) ──
    for gid, von, bis, preis in [
        ('GP_RLT_10K', 0, 10000, 600.00),
        ('GP_RLT_50K', 10001, 50000, 780.00),
        ('GP_RLT_GROSS', 50001, 999999, 1100.00),
    ]:
        statements.append(f"""
        CREATE (:Grundpreis {{id: '{gid}', von_volumenstrom: {von}, bis_volumenstrom: {bis}, betrag: {preis}, quelle: 'LPV B05 Kap. 2.1'}})
        """)
    statements.append("""
    MATCH (p:Produkt {id: 'RLT_STANDARD'}), (g:Grundpreis)
    WHERE g.id STARTS WITH 'GP_RLT'
    CREATE (p)-[:HAT_GRUNDPREIS]->(g)
    """)

    # ── 4. STÜCKZUSCHLÄGE ────────────────────────────────────
    statements.append("""
    CREATE (:ZuschlagStueck {id: 'ZS_VENTILATOR', name: 'Ventilator', betrag_pro_stueck: 170.00, quelle: 'LPV B05 Kap. 2'})
    """)
    statements.append("""
    CREATE (:ZuschlagStueck {id: 'ZS_BSK', name: 'Brandschutzklappe', betrag_pro_stueck: 40.00, quelle: 'LPV B05 Kap. 2'})
    """)
    statements.append("""
    MATCH (p:Produkt {id: 'RLT_GARAGE'}), (z:ZuschlagStueck)
    CREATE (p)-[:HAT_ZUSCHLAG_STK]->(z)
    """)

    # ── 5. GRUNDKOSTEN (shared) ──────────────────────────────
    statements.append("""
    CREATE (:Grundkosten {id: 'GRUND_PAUSCHALE', name: 'Pauschale Auftragsanlage', betrag: 256.00, quelle: 'LPV Teil A'})
    """)
    statements.append("""
    CREATE (:Grundkosten {id: 'GRUND_ORDNUNG', name: 'Ordnungsprüfung Dokumente', betrag: 242.00, bedingung: 'nur bei baurechtlichen Prüfungen', quelle: 'LPV Teil A'})
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
        CREATE (:Berichtstyp {{id: '{bid}', name: '{name}', betrag: {betrag}, quelle: 'LPV B05'}})
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

    # ── 11. STANDORTE (23 TÜV-Niederlassungen) ──────────────
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

    # ── 12. PRUEFTAGE-SCHÄTZUNG ──────────────────────────────
    # HYG
    statements.append("""
    CREATE (:Prueftagschaetzung {id: 'PT_HYG', typ: 'hygiene', formel: 'max(0.5, bereiche * 0.4)', quelle: 'Heuristik'})
    """)
    # GARAGE
    for pid, von, bis, tage in [
        ('PT_GAR_KLEIN', 1, 30, 0.5),
        ('PT_GAR_MITTEL', 31, 100, 1.0),
        ('PT_GAR_GROSS', 101, 9999, 2.0),
    ]:
        statements.append(f"""
        CREATE (:Prueftagschaetzung {{id: '{pid}', typ: 'garage', von_stellplaetze: {von}, bis_stellplaetze: {bis}, tage: {tage}, quelle: 'Heuristik'}})
        """)

    # ── 13. CROSS-SELL ───────────────────────────────────────
    statements.append("""
    CREATE (:CrossSell {id: 'CS_BLITZ', empfehlung: 'Blitzschutzprüfung — Kombi-Begehung spart Reisekosten', produkt: 'blitzschutz', prioritaet: 'hoch'})
    """)
    statements.append("""
    CREATE (:CrossSell {id: 'CS_BMA', empfehlung: 'Brandmeldeanlage — gleiche Begehung möglich', produkt: 'bma', prioritaet: 'mittel'})
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
