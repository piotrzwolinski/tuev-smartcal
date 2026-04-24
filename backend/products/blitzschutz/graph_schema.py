"""Load Blitzschutz pricing rules into FalkorDB graph.

All rules from LPV 2025/2026 + TÜV-Korrespondenz as graph nodes + relationships.
This replaces hardcoded Python constants — engine queries graph instead.

Usage:
    from products.blitzschutz.graph_schema import load_blitzschutz_graph
    stats = load_blitzschutz_graph()
"""

from common.database import get_graph, query

GRAPH_NAME = "blitzschutz"


def load_blitzschutz_graph() -> dict:
    """Load complete Blitzschutz pricing rules into FalkorDB graph."""
    graph = get_graph(GRAPH_NAME)

    # Clear existing
    graph.query("MATCH (n) DETACH DELETE n")

    statements = []

    # ──────────────────────────────────────────────────────────────
    # 1. PRODUKTE
    # ──────────────────────────────────────────────────────────────
    statements.append("""
    CREATE (:Produkt {
        id: 'BLITZ_AUSSEN',
        name: 'Prüfung Blitzschutzanlagen — Äußerer Blitzschutz',
        lpv_referenz: 'B04 §8.1',
        einheit: 'Messstelle',
        preis_pro_einheit: 33.00,
        schwelle_vereinbarung: 10,
        stundensatz: 180.00,
        beschreibung: 'Die Prüfung der äußeren Blitzschutzanlage wird nach Aufwand, zu einem Festpreis oder Abhängig von der Anzahl der Messstellen verrechnet.'
    })
    """)

    statements.append("""
    CREATE (:Produkt {
        id: 'BLITZ_INNEN',
        name: 'Innerer Blitzschutz, Überspannungsschutz',
        lpv_referenz: 'B04 §8.2',
        verrechnung: 'nach_angebot',
        stundensatz: 208.00,
        beschreibung: 'Bei der Beurteilung des Blitzschutz-Potentialausgleichs sowie bei der Ausarbeitung eines Blitzschutzkonzeptes für Starkstrom- oder Fernmeldeanlagen erfolgt die Verrechnung auf der Grundlage eines Angebots.'
    })
    """)

    statements.append("""
    CREATE (:Produkt {
        id: 'BLITZ_EX',
        name: 'Blitzschutz im Explosionsschutzbereich',
        lpv_referenz: 'B04 §9',
        verrechnung: 'nach_besonderer_vereinbarung',
        stundensatz: 239.00,
        beschreibung: 'Die Prüfung des Explosionsschutzes in explosionsgefährdeten Bereichen (Lageranlagen, Füllstellen, Tankstellen) gemäß ÜAnlG wird nach besonderer Vereinbarung verrechnet.'
    })
    """)

    # ──────────────────────────────────────────────────────────────
    # 2. STAFFELN (>10 Messstellen)
    # ──────────────────────────────────────────────────────────────
    statements.append("""
    CREATE (:Staffel {id: 'STAFFEL_1', von: 1,  bis: 10,  preis_pro_ms: 33.00, quelle: 'LPV B04 §8.1', typ: 'lpv_konform'})
    """)
    statements.append("""
    CREATE (:Staffel {id: 'STAFFEL_2', von: 11, bis: 20,  preis_pro_ms: 30.00, quelle: 'Heuristik (StV-Validierung)', typ: 'heuristik'})
    """)
    statements.append("""
    CREATE (:Staffel {id: 'STAFFEL_3', von: 21, bis: 40,  preis_pro_ms: 28.00, quelle: 'Heuristik (StV-Validierung)', typ: 'heuristik'})
    """)
    statements.append("""
    CREATE (:Staffel {id: 'STAFFEL_4', von: 41, bis: 100, preis_pro_ms: 26.00, quelle: 'Heuristik (StV-Validierung)', typ: 'heuristik'})
    """)
    statements.append("""
    CREATE (:Staffel {id: 'STAFFEL_5', von: 101, bis: 500, preis_pro_ms: 24.00, quelle: 'Heuristik (StV-Validierung)', typ: 'heuristik'})
    """)

    # Link Staffeln → Produkt
    statements.append("""
    MATCH (p:Produkt {id: 'BLITZ_AUSSEN'}), (s:Staffel)
    CREATE (p)-[:HAT_STAFFEL]->(s)
    """)

    # ──────────────────────────────────────────────────────────────
    # 3. GRUNDKOSTEN
    # ──────────────────────────────────────────────────────────────
    statements.append("""
    CREATE (:Grundkosten {
        id: 'GRUND_PAUSCHALE',
        name: 'Pauschale Auftragsanlage, Verwaltung, Angebotsgebühr',
        betrag: 256.00,
        quelle: 'LPV Teil A + TÜV-Korrespondenz'
    })
    """)
    statements.append("""
    CREATE (:Grundkosten {
        id: 'GRUND_ORDNUNG',
        name: 'Pauschale Ordnungsprüfung Dokumente',
        betrag: 242.00,
        bedingung: 'nur bei baurechtlichen Prüfungen',
        quelle: 'LPV Teil A + TÜV-Korrespondenz: nicht im aktuellen Beispiel'
    })
    """)
    statements.append("""
    CREATE (:Grundkosten {
        id: 'GRUND_PRUEFMITTEL',
        name: 'Energie- und Prüfmittelpauschale',
        betrag_pro_tag: 49.00,
        einheit: 'je Prüftag, je Sachverständiger',
        quelle: 'LPV Teil A §4 + TÜV-Korrespondenz'
    })
    """)

    # ──────────────────────────────────────────────────────────────
    # 4. TAGEGELD
    # ──────────────────────────────────────────────────────────────
    statements.append("""
    CREATE (:Tagegeld {id: 'TG_6_8',   von_h: 6,  bis_h: 8,  betrag: 6.00,  quelle: 'LPV Teil A §4.3'})
    """)
    statements.append("""
    CREATE (:Tagegeld {id: 'TG_8_14',  von_h: 8,  bis_h: 14, betrag: 25.00, quelle: 'LPV Teil A §4.3'})
    """)
    statements.append("""
    CREATE (:Tagegeld {id: 'TG_14_24', von_h: 14, bis_h: 24, betrag: 30.00, quelle: 'LPV Teil A §4.3'})
    """)

    # ──────────────────────────────────────────────────────────────
    # 5. STUNDENSÄTZE
    # ──────────────────────────────────────────────────────────────
    for sid, name, betrag in [
        ('STD_EINFACH', 'Einfache Sachverhalte', 180.00),
        ('STD_SCHWIERIG', 'Schwierige Sachverhalte', 208.00),
        ('STD_KOMPLEX', 'Komplexe Sachverhalte', 239.00),
        ('STD_BESONDERS', 'Besondere Sachverhalte', 265.00),
        ('STD_SYSTEM', 'Systemanalysen', 320.00),
    ]:
        statements.append(f"""
        CREATE (:Stundensatz {{id: '{sid}', name: '{name}', betrag: {betrag}, quelle: 'LPV Teil A §4.2'}})
        """)

    # ──────────────────────────────────────────────────────────────
    # 6. REISEKOSTEN
    # ──────────────────────────────────────────────────────────────
    statements.append("""
    CREATE (:Reisekostenregel {
        id: 'RK_PKW',
        name: 'Kilometergeld PKW',
        betrag_pro_km: 1.10,
        quelle: 'LPV Teil A §4.3'
    })
    """)
    statements.append("""
    CREATE (:Reisekostenregel {
        id: 'RK_LKW',
        name: 'Kilometergeld LKW-Gerätewagen',
        betrag_pro_km: 1.20,
        quelle: 'LPV Teil A §4.3'
    })
    """)
    statements.append("""
    CREATE (:Reisekostenregel {
        id: 'RK_MEHRTAEGIG',
        name: 'Bei mehrtägigen Prüfungen',
        regel: 'nur 1 Hin-/Rückfahrt',
        quelle: 'TÜV-Korrespondenz 14.08.2025'
    })
    """)

    # ──────────────────────────────────────────────────────────────
    # 7. BERICHTERSTELLUNG
    # ──────────────────────────────────────────────────────────────
    statements.append("""
    CREATE (:Berichtstyp {id: 'BER_KLEIN',    name: 'Kleine Anlagen (Blitzschutz)',       betrag: 119.00, quelle: 'TÜV-Korrespondenz'})
    """)
    statements.append("""
    CREATE (:Berichtstyp {id: 'BER_STANDARD',  name: 'Standardbericht bis 10 Seiten',     betrag: 380.00, quelle: 'LPV B04 §11'})
    """)
    statements.append("""
    CREATE (:Berichtstyp {id: 'BER_KOMPLEX',   name: 'Komplex/besonderer Sachverhalt',     betrag: 550.00, quelle: 'LPV B04 §11'})
    """)
    statements.append("""
    CREATE (:Berichtstyp {id: 'BER_INDIVIDUELL', name: 'Individueller Begutachtungsbericht', betrag: -1, verrechnung: 'n.V.', quelle: 'LPV B04 §11'})
    """)

    # Zuordnung Berichtstyp per MS-range (Heuristik)
    statements.append("""
    MATCH (p:Produkt {id: 'BLITZ_AUSSEN'}), (b:Berichtstyp {id: 'BER_KLEIN'})
    CREATE (p)-[:HAT_BERICHTSTYP {bedingung: 'messstellen <= 10', typ: 'heuristik'}]->(b)
    """)
    statements.append("""
    MATCH (p:Produkt {id: 'BLITZ_AUSSEN'}), (b:Berichtstyp {id: 'BER_STANDARD'})
    CREATE (p)-[:HAT_BERICHTSTYP {bedingung: 'messstellen > 10 AND messstellen <= 40', typ: 'heuristik'}]->(b)
    """)
    statements.append("""
    MATCH (p:Produkt {id: 'BLITZ_AUSSEN'}), (b:Berichtstyp {id: 'BER_KOMPLEX'})
    CREATE (p)-[:HAT_BERICHTSTYP {bedingung: 'messstellen > 40', typ: 'heuristik'}]->(b)
    """)

    # ──────────────────────────────────────────────────────────────
    # 8. ZUSCHLÄGE
    # ──────────────────────────────────────────────────────────────
    for zid, name, prozent, bedingung, quelle in [
        ('ZS_NICHT_VEREIN', 'Nicht-Vereinsmitglied', 0.20, 'kein Rahmenvertrag/Vereinsmitgliedschaft', 'LPV Teil A'),
        ('ZS_EINZELPRUEFUNG', 'Einzelprüfung ohne Rahmenvertrag', 0.20, 'keine vertragliche Vereinbarung', 'LPV Teil A §5.2'),
        ('ZS_ERSTPRUEFUNG', 'Erstprüfung vor Inbetriebnahme', 1.00, 'Prüfung vor erster Inbetriebnahme', 'LPV Teil A §5.2'),
        ('ZS_EIL', 'Eilzuschlag / Sondertermin', 0.25, 'bevorzugte Bearbeitung innerhalb 2 Wochen', 'LPV Teil A §11'),
        ('ZS_EIL_MAX', 'Bevorzugte Bearbeitung maximal', 1.00, 'auf Antrag bevorzugt', 'LPV Teil A §11'),
        ('ZS_AUSSERHALB', 'Außerhalb normaler Dienstzeit', 1.00, 'Leistungen außerhalb Dienstzeit', 'LPV Teil A §11'),
    ]:
        statements.append(f"""
        CREATE (:Zuschlag {{id: '{zid}', name: '{name}', prozent: {prozent}, bedingung: '{bedingung}', quelle: '{quelle}'}})
        """)

    # ──────────────────────────────────────────────────────────────
    # 9. SCHUTZKLASSEN
    # ──────────────────────────────────────────────────────────────
    for skid, name, beschreibung in [
        ('SK_I', 'Schutzklasse I', 'Höchste (Explosionsgefahr, Munition)'),
        ('SK_II', 'Schutzklasse II', 'Krankenhaus, Museum, Versammlungsstätten'),
        ('SK_III', 'Schutzklasse III', 'Standard (Büro, Industrie, Wohnung, Schule)'),
        ('SK_IV', 'Schutzklasse IV', 'Niedrigste (einfache Wohngebäude, Lager)'),
    ]:
        statements.append(f"""
        CREATE (:Schutzklasse {{id: '{skid}', name: '{name}', beschreibung: '{beschreibung}'}})
        """)

    # ──────────────────────────────────────────────────────────────
    # 10. GEBÄUDETYPEN + typische Schutzklasse + Trennstellen-Range
    # ──────────────────────────────────────────────────────────────
    gebaeudetypen = [
        ('GT_SCHULE', 'Schule / Kindergarten', 'SK_III', 6, 35),
        ('GT_BUERO', 'Bürogebäude', 'SK_III', 6, 28),
        ('GT_INDUSTRIE', 'Industriegebäude', 'SK_III', 12, 60),
        ('GT_WOHNUNG', 'Wohngebäude', 'SK_IV', 3, 12),
        ('GT_HOTEL', 'Hotel / Gaststätte', 'SK_III', 8, 30),
        ('GT_MUSEUM', 'Museum / Burg / Schloss', 'SK_II', 18, 48),
        ('GT_KRANKENHAUS', 'Krankenhaus / Klinik', 'SK_II', 30, 180),
        ('GT_LAGER', 'Lager / Halle', 'SK_IV', 6, 40),
        ('GT_GARAGE', 'Garage / Parkhaus', 'SK_IV', 4, 20),
    ]
    for gtid, name, typ_sk, ts_min, ts_max in gebaeudetypen:
        statements.append(f"""
        CREATE (:Gebaeudetyp {{id: '{gtid}', name: '{name}', typische_ts_min: {ts_min}, typische_ts_max: {ts_max}}})
        """)
        # Link to typical Schutzklasse
        statements.append(f"""
        MATCH (g:Gebaeudetyp {{id: '{gtid}'}}), (s:Schutzklasse {{id: '{typ_sk}'}})
        CREATE (g)-[:TYPISCHE_SCHUTZKLASSE]->(s)
        """)

    # ──────────────────────────────────────────────────────────────
    # 11. STANDORTE (23 TÜV-Niederlassungen, exakte Adressen)
    # ──────────────────────────────────────────────────────────────
    standorte = [
        ('AUG', 'Augsburg', 'Oskar-von-Miller-Straße 17', '86199', 48.3543, 10.8735),
        ('BER', 'Berlin', 'Wittestraße 30, Haus LM', '13509', 52.5785, 13.3195),
        ('DAR', 'Darmstadt', 'Rüdesheimer Straße 119', '64285', 49.8590, 8.6365),
        ('DRE', 'Dresden', 'Drescherhäuser 5 D', '01159', 51.0580, 13.6940),
        ('ESS', 'Essen', 'Kruppstraße 82-100', '45145', 51.4470, 6.9880),
        ('FIL', 'Filderstadt', 'Gottlieb-Daimler-Straße 7', '70794', 48.6560, 9.2200),
        ('FRE', 'Freiburg', 'Hermann-Mitsch-Straße 36 A', '79108', 48.0200, 7.8340),
        ('HAM', 'Hamburg', 'Syltsterstraße 2', '22525', 53.5740, 9.9270),
        ('HAN', 'Hannover', 'Göttinger Landstraße 10', '30419', 52.3870, 9.7100),
        ('HEI', 'Heilbronn', 'Heiner-Daimler-Straße 9', '74076', 49.1380, 9.2230),
        ('HOF', 'Hof', 'Erfreudenstraße 75', '95032', 50.3100, 11.9250),
        ('KAR', 'Karlsruhe', 'Am Rüppurer Schloß 1', '76199', 48.9870, 8.3990),
        ('LEI', 'Leipzig', 'Weserstraße 2', '04159', 51.3680, 12.3410),
        ('MAN', 'Mannheim', 'Dudenstraße 28', '68167', 49.4930, 8.4800),
        ('MUC', 'München', 'Westendstraße 199', '80686', 48.1420, 11.5170),
        ('NBG', 'Nürnberg', 'Edisonstraße 15', '90431', 49.4440, 11.0250),
        ('RAV', 'Ravensburg', 'Rudolfstraße 15', '88214', 47.7820, 9.6120),
        ('RGB', 'Regensburg', 'Friedenstraße 6', '93051', 49.0100, 12.0840),
        ('ROS', 'Rostock', 'Krusensternweg 2', '18069', 54.0810, 12.1070),
        ('SBR', 'St. Ingbert', 'Am Alten Forsthaus 1', '66386', 49.2770, 7.1150),
        ('TRT', 'Trostberg', 'Gabelsbergerstraße 5', '83308', 48.0260, 12.5450),
        ('ULM', 'Ulm', 'Berlinger Straße 17', '89079', 48.3780, 9.9590),
        ('WZB', 'Würzburg', 'Petrinstraße 33 A', '97080', 49.7830, 9.9400),
    ]
    for sid, name, adresse, plz, lat, lon in standorte:
        statements.append(f"""
        CREATE (:Standort {{id: 'STD_{sid}', name: '{name}', adresse: '{adresse}', plz: '{plz}', lat: {lat}, lon: {lon}, quelle: 'TÜV-Korrespondenz 14.08.2025'}})
        """)

    # ──────────────────────────────────────────────────────────────
    # 12. PRÜFTAGE-SCHÄTZUNG (Heuristik)
    # ──────────────────────────────────────────────────────────────
    for pid, von, bis, tage in [
        ('PT_1', 1, 10, 0.5),
        ('PT_2', 11, 30, 1.0),
        ('PT_3', 31, 60, 2.0),
        ('PT_4', 61, 100, 3.0),
        ('PT_5', 101, 500, -1),  # -1 = Formel: ms/40
    ]:
        statements.append(f"""
        CREATE (:Prueftagschaetzung {{id: '{pid}', von_ms: {von}, bis_ms: {bis}, tage: {tage}, formel: '{"ms/40" if tage == -1 else ""}', quelle: 'Heuristik', typ: 'heuristik'}})
        """)

    # ──────────────────────────────────────────────────────────────
    # 13. CROSS-SELL
    # ──────────────────────────────────────────────────────────────
    statements.append("""
    MATCH (a:Produkt {id:'BLITZ_AUSSEN'}), (b:Produkt {id:'BLITZ_INNEN'})
    CREATE (a)-[:EMPFIEHLT {
        text: 'Für vollständige Beurteilung: innerer Blitzschutz + Überspannungsschutz empfohlen',
        prioritaet: 'hoch'
    }]->(b)
    """)

    # Execute all
    for stmt in statements:
        try:
            graph.query(stmt.strip())
        except Exception as e:
            print(f"ERROR: {e}\n  Statement: {stmt.strip()[:100]}")

    # Stats
    nodes = graph.query("MATCH (n) RETURN count(n) AS cnt").result_set[0][0]
    edges = graph.query("MATCH ()-[r]->() RETURN count(r) AS cnt").result_set[0][0]
    labels = graph.query("MATCH (n) RETURN DISTINCT labels(n)[0] AS l, count(n) AS c ORDER BY c DESC")

    return {
        "graph": GRAPH_NAME,
        "nodes": nodes,
        "edges": edges,
        "labels": {row[0]: row[1] for row in labels.result_set},
    }
