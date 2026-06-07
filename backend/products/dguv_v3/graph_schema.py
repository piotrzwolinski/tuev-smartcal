"""Load DGUV V3 pricing rules into FalkorDB graph.

PRD v2.1 — All nodes with provenance metadata (_quelle, _typ, _stand).
Includes: Installationskategorien (calibrated), NutzungsMapping, Branchenfragen,
Umrechnungsregeln, Reifegrad, Dokumentation, Preissteigerung, Referenzobjekte.
"""

from common.database import get_graph

GRAPH_NAME = "dguv_v3"
STAND = "2026-05-30"


def load_dguv_graph() -> dict:
    graph = get_graph(GRAPH_NAME)
    graph.query("MATCH (n) DETACH DELETE n")

    statements = []

    # ── 1. PRODUKT ───────────────────────────────────────────
    statements.append(f"""
    CREATE (:Produkt {{
        id: 'DGUV_V3_ORTSFEST',
        name: 'DGUV V3 ortsfeste elektrische Anlage',
        lpv_referenz: 'B04 Kap. 2',
        grundpreis: 250.00,
        beschreibung: 'Wiederkehrende Prüfung ortsfester elektrischer Anlagen nach DIN VDE 0105-100/A1 und DGUV Vorschrift 3.',
        _quelle: 'LPV B04 Kap. 2', _typ: 'regel', _stand: '{STAND}'
    }})
    """)

    # ── 2. INSTALLATIONSKATEGORIEN (calibrated to NBG) ──────
    for kid, name, preis, beschreibung, quelle, typ in [
        ('KAT_1', 'Wohnung / Freiflächen / Allgemeinbereiche', 1.00, 'Allgemeinbereiche Wohngebäude, Freiflächen in Außenanlagen', 'Kalkulationshilfen NBG / Hilfstabellen / 2026', 'regel'),
        ('KAT_2', 'Büro / Schule / Restaurant / Lager / Krankenhaus', 3.10, 'Büro- oder Wohnräume, Gasträume, Schulen, Werkstätten, Laborbereiche, Alten-/Pflegeheim', 'Kalkulationshilfen NBG / Hilfstabellen / 2026', 'regel'),
        ('KAT_3', 'Supermarkt / Produktion / Museum / EDV', 5.00, 'Ausstellungsbereiche, Großdruckereien, Produktionsmaschinen, Versammlungsräume, Verkaufsräume', 'Kalkulationshilfen NBG / Hilfstabellen / 2026', 'regel'),
        ('KAT_4', 'Technikräume / Reinraum', 5.40, 'Technikräume, Reinraum', 'Kalkulationshilfen NBG / Hilfstabellen / 2026', 'regel'),
        ('KAT_5', 'Sonderfläche (OP, Labor)', 5.40, 'OP-Saal, Reinraum, Ex-Bereich', 'Kalkulationshilfen NBG / Hilfstabellen / 2026', 'regel'),
        ('KAT_6', 'NSHV / Trafo / Batterieladestation', 6.00, 'Technikräume, NSHV, Traforäume, Batterieladestationen', 'S. Veit Mail 30.05 Punkt 4', 'fachexperte'),
    ]:
        statements.append(f"""
        CREATE (:Installationskategorie {{id: '{kid}', name: '{name}', preis_per_10m2: {preis}, beschreibung: '{beschreibung}', _quelle: '{quelle}', _typ: '{typ}', _stand: '{STAND}'}})
        """)
    statements.append(f"""
    MATCH (p:Produkt {{id: 'DGUV_V3_ORTSFEST'}}), (k:Installationskategorie)
    CREATE (p)-[:HAT_KATEGORIE]->(k)
    """)

    # ── 3. VERTEILUNGEN ──────────────────────────────────────
    for vid, name, preis in [
        ('VERT_UV', 'Unterverteilung (UV)', 25.00),
        ('VERT_HV', 'Hauptverteilung (HV)', 85.00),
        ('VERT_NSHV', 'Niederspannungshauptverteilung (NSHV)', 145.00),
    ]:
        statements.append(f"""
        CREATE (:Verteilung {{id: '{vid}', name: '{name}', preis_pro_einheit: {preis}, _quelle: 'LPV B04 Kap. 2', _typ: 'regel', _stand: '{STAND}'}})
        """)
    statements.append("MATCH (p:Produkt {id: 'DGUV_V3_ORTSFEST'}), (v:Verteilung) CREATE (p)-[:HAT_VERTEILUNG]->(v)")

    # ── 4. SONDERZUSCHLÄGE ──────────────────────────────────
    statements.append(f"CREATE (:Sonderzuschlag {{id: 'SZ_NEA', name: 'Netzersatzanlage (NEA)', betrag: 320.00, _quelle: 'LPV B04 Kap. 2', _typ: 'regel', _stand: '{STAND}'}})")
    statements.append(f"CREATE (:Sonderzuschlag {{id: 'SZ_SV_NSHV', name: 'Sicherheitsstromversorgung NSHV', betrag: 180.00, _quelle: 'LPV B04 Kap. 2', _typ: 'regel', _stand: '{STAND}'}})")
    statements.append("MATCH (p:Produkt {id: 'DGUV_V3_ORTSFEST'}), (s:Sonderzuschlag) CREATE (p)-[:HAT_SONDERZUSCHLAG]->(s)")

    # ── 5. GRUNDKOSTEN (shared) ──────────────────────────────
    statements.append(f"CREATE (:Grundkosten {{id: 'GRUND_PAUSCHALE', name: 'Pauschale Auftragsanlage', betrag: 256.00, _quelle: 'LPV Teil A', _typ: 'regel', _stand: '{STAND}'}})")
    statements.append(f"CREATE (:Grundkosten {{id: 'GRUND_ORDNUNG', name: 'Ordnungsprüfung Dokumente', betrag: 242.00, bedingung: 'nur baurechtlich', _quelle: 'LPV Teil A', _typ: 'regel', _stand: '{STAND}'}})")
    statements.append(f"CREATE (:Grundkosten {{id: 'GRUND_PRUEFMITTEL', name: 'Energie-/Prüfmittelpauschale', betrag_pro_tag: 49.00, _quelle: 'LPV Teil A §4', _typ: 'regel', _stand: '{STAND}'}})")

    # ── 6. STUNDENSÄTZE ──────────────────────────────────────
    for sid, name, betrag in [('STD_EINFACH', 'Einfache Sachverhalte', 180.00), ('STD_SCHWIERIG', 'Schwierige Sachverhalte', 208.00), ('STD_KOMPLEX', 'Komplexe Sachverhalte', 239.00)]:
        statements.append(f"CREATE (:Stundensatz {{id: '{sid}', name: '{name}', betrag: {betrag}, _quelle: 'LPV Teil A §4.2', _typ: 'regel', _stand: '{STAND}'}})")

    # ── 7. REISEKOSTEN ───────────────────────────────────────
    statements.append(f"CREATE (:Reisekostenregel {{id: 'RK_PKW', name: 'Kilometergeld PKW', betrag_pro_km: 1.10, _quelle: 'LPV Teil A §4.3', _typ: 'regel', _stand: '{STAND}'}})")

    # ── 8. TAGEGELD ──────────────────────────────────────────
    for tid, von, bis, betrag in [('TG_6_8', 6, 8, 6.00), ('TG_8_14', 8, 14, 25.00), ('TG_14_24', 14, 24, 30.00)]:
        statements.append(f"CREATE (:Tagegeld {{id: '{tid}', von_h: {von}, bis_h: {bis}, betrag: {betrag}, _quelle: 'LPV Teil A §4.3', _typ: 'regel', _stand: '{STAND}'}})")

    # ── 9. BERICHTSTYPEN ─────────────────────────────────────
    for bid, name, betrag in [('BER_KLEIN', 'Kleine Anlagen', 119.00), ('BER_STANDARD', 'Standardbericht', 380.00), ('BER_KOMPLEX', 'Komplexer Sachverhalt', 550.00)]:
        statements.append(f"CREATE (:Berichtstyp {{id: '{bid}', name: '{name}', betrag: {betrag}, _quelle: 'LPV B04', _typ: 'regel', _stand: '{STAND}'}})")

    # ── 10. ZUSCHLÄGE (prozentual) ───────────────────────────
    for zid, name, prozent, bedingung in [
        ('ZS_NICHT_VEREIN', 'Nicht-Vereinsmitglied', 0.20, 'kein Rahmenvertrag'),
        ('ZS_ERSTPRUEFUNG', 'Erstprüfung', 1.00, 'vor erster Inbetriebnahme'),
        ('ZS_EIL', 'Eilzuschlag', 0.25, 'bevorzugte Bearbeitung'),
    ]:
        statements.append(f"CREATE (:Zuschlag {{id: '{zid}', name: '{name}', prozent: {prozent}, bedingung: '{bedingung}', _quelle: 'LPV Teil A', _typ: 'regel', _stand: '{STAND}'}})")

    # ── 11. GEBÄUDETYPEN ─────────────────────────────────────
    gebaeudetypen = [
        ('GT_BUERO', 'Bürogebäude', 'KAT_2', 100, 5000),
        ('GT_SERVICE', 'Service Center', 'KAT_2', 200, 3000),
        ('GT_SENIOR', 'Seniorentreff', 'KAT_2', 50, 1000),
        ('GT_HOTEL', 'Hotel', 'KAT_2', 500, 15000),
        ('GT_KRANKENHAUS', 'Krankenhaus', 'KAT_2', 2000, 100000),
        ('GT_INDUSTRIE', 'Industriegebäude', 'KAT_3', 500, 50000),
        ('GT_SCHULE', 'Schule', 'KAT_2', 500, 10000),
        ('GT_VERKAUF', 'Verkaufsstätte', 'KAT_3', 200, 20000),
        ('GT_TIEFGARAGE', 'Tiefgarage', 'KAT_1', 200, 20000),
        ('GT_VERSAMMLUNG', 'Versammlungsstätte', 'KAT_3', 200, 30000),
        ('GT_MOEBEL', 'Möbelhaus', 'KAT_3', 500, 30000),
        ('GT_GARTEN', 'Gartenmarkt', 'KAT_3', 500, 20000),
    ]
    for gtid, name, typ_kat, fl_min, fl_max in gebaeudetypen:
        statements.append(f"""
        CREATE (:Gebaeudetyp {{id: '{gtid}', name: '{name}', typische_flaeche_min: {fl_min}, typische_flaeche_max: {fl_max}, _quelle: 'Kalkulationshilfen NBG + S. Veit', _typ: 'regel', _stand: '{STAND}'}})
        """)
        statements.append(f"""
        MATCH (g:Gebaeudetyp {{id: '{gtid}'}}), (k:Installationskategorie {{id: '{typ_kat}'}})
        CREATE (g)-[:TYPISCHE_KATEGORIE {{_quelle: 'Kalkulationshilfen NBG', _typ: 'regel'}}]->(k)
        """)

    # ── 12. STANDORTE ────────────────────────────────────────
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
        statements.append(f"CREATE (:Standort {{id: 'STD_{sid}', name: '{name}', lat: {lat}, lon: {lon}, _quelle: 'TÜV-Korrespondenz', _typ: 'regel', _stand: '{STAND}'}})")

    # ── 13. PRUEFTAGE ────────────────────────────────────────
    for pid, von, bis, tage in [('PT_1', 1, 500, 0.5), ('PT_2', 501, 2000, 1.0), ('PT_3', 2001, 5000, 2.0), ('PT_4', 5001, 999999, -1)]:
        statements.append(f"CREATE (:Prueftagschaetzung {{id: '{pid}', von_m2: {von}, bis_m2: {bis}, tage: {tage}, formel: '{'flaeche/2500' if tage == -1 else ''}', _quelle: 'Heuristik', _typ: 'statistik', _stand: '{STAND}'}})")

    # ── 14. CROSS-SELL ───────────────────────────────────────
    statements.append(f"CREATE (:CrossSell {{id: 'CS_BLITZ', empfehlung: 'Blitzschutzprüfung — Kombi-Begehung spart Reisekosten', produkt: 'blitzschutz', prioritaet: 'hoch', _quelle: 'S. Veit erster Call', _typ: 'fachexperte', _stand: '{STAND}'}})")
    statements.append(f"CREATE (:CrossSell {{id: 'CS_RLT', empfehlung: 'RLT-Hygieneinspektion (VDI 6022) — gleiche Begehung möglich', produkt: 'rlt', prioritaet: 'mittel', _quelle: 'S. Veit erster Call', _typ: 'fachexperte', _stand: '{STAND}'}})")

    # ══════════════════════════════════════════════════════════
    # NEW PRD v2.1 NODES
    # ══════════════════════════════════════════════════════════

    # ── 15. BRANCHENFRAGEN ───────────────────────────────────
    branchenfragen = [
        ('BF_HOTEL', 'Hotel', 'Wie viele Zimmer hat das Hotel?', 'Restaurant vorhanden?,Spa/Wellness vorhanden?,Konferenzbereiche vorhanden?'),
        ('BF_KRANKENHAUS', 'Krankenhaus', 'Wie viele Betten?', 'OP-Bereich vorhanden?,Intensivstation?'),
        ('BF_SCHULE', 'Schule', 'Wie viele Klassenräume?', 'Turnhalle vorhanden?,Werkräume vorhanden?'),
        ('BF_TIEFGARAGE', 'Tiefgarage', 'Wie viele Stellplätze?', ''),
        ('BF_SUPERMARKT', 'Supermarkt', 'Wie groß ist die Verkaufsfläche in m²?', 'Frischetheke vorhanden?,Bäckerei vorhanden?'),
        ('BF_INDUSTRIE', 'Industrie/Logistik', 'Wie verteilt sich die Nutzung? (% Verwaltung, Produktion, Logistik, Technik)', ''),
        ('BF_VERWALTUNG', 'Verwaltungsgebäude', 'Wie groß ist die Bürofläche in m²?', 'Kantine vorhanden?,Rechenzentrum vorhanden?,Tiefgarage/Stellplätze?'),
        ('BF_MOEBEL', 'Möbelhaus/Gartenmarkt', 'Verkaufsfläche, Lagerfläche, Außenfläche in m²?', ''),
    ]
    for bfid, gtyp, frage, zusatz in branchenfragen:
        zusatz_escaped = zusatz.replace("'", "\\'")
        frage_escaped = frage.replace("'", "\\'")
        statements.append(f"""
        CREATE (:Branchenfrage {{id: '{bfid}', gebaeudetyp: '{gtyp}', frage: '{frage_escaped}', zusatzfragen: '{zusatz_escaped}', _quelle: 'S. Veit Mail 30.05 Punkt 2', _typ: 'fachexperte', _stand: '{STAND}'}})
        """)

    # ── 16. UMRECHNUNGSREGELN ────────────────────────────────
    umrechnungen = [
        ('UR_ZIMMER', 'Hotel', 'Zimmeranzahl', 30.0, '25-45 je nach Hotelklasse'),
        ('UR_BETTEN', 'Krankenhaus', 'Bettenanzahl', 50.0, '40-70'),
        ('UR_KLASSEN', 'Schule', 'Klassenräume', 70.0, '60-80'),
        ('UR_STELLPL', 'Tiefgarage', 'Stellplätze', 25.0, '20-30'),
        ('UR_MA', 'Büro', 'Mitarbeiter', 15.0, '10-20'),
        ('UR_SITZE', 'Versammlungsstätte', 'Sitzplätze', 3.0, '2-5'),
    ]
    for urid, gtyp, merkmal, faktor, varianz in umrechnungen:
        statements.append(f"""
        CREATE (:Umrechnungsregel {{id: '{urid}', gebaeudetyp: '{gtyp}', kundenmerkmal: '{merkmal}', faktor_m2: {faktor}, varianz: '{varianz}', _quelle: 'Branchenwissen', _typ: 'llm_augmentiert', _stand: '{STAND}'}})
        """)

    # ── 17. NUTZUNGSMAPPING ──────────────────────────────────
    nutzungsmappings = [
        ('NM_WOHNUNG', 'Wohnung', 'KAT_1'), ('NM_FREIFL', 'Freifläche', 'KAT_1'), ('NM_ALLGEM', 'Allgemeinbereich', 'KAT_1'),
        ('NM_BUERO', 'Büro', 'KAT_2'), ('NM_SCHULE', 'Schule', 'KAT_2'), ('NM_RESTAURANT', 'Restaurant', 'KAT_2'),
        ('NM_LAGER', 'Lager', 'KAT_2'), ('NM_LOGISTIK', 'Logistik', 'KAT_2'), ('NM_KRANKENH', 'Krankenhaus', 'KAT_2'),
        ('NM_ALTENH', 'Altenheim', 'KAT_2'), ('NM_WERKST', 'Werkstatt', 'KAT_2'), ('NM_HOTEL', 'Hotel', 'KAT_2'),
        ('NM_SUPERM', 'Supermarkt', 'KAT_3'), ('NM_PRODUKTION', 'Produktion', 'KAT_3'), ('NM_MUSEUM', 'Museum', 'KAT_3'),
        ('NM_EDV', 'EDV-Zentrale', 'KAT_3'), ('NM_VERSAMML', 'Versammlungsraum', 'KAT_3'), ('NM_VERKAUF', 'Verkaufsfläche', 'KAT_3'),
        ('NM_TECHNIK', 'Technikraum', 'KAT_4'), ('NM_REINRAUM', 'Reinraum', 'KAT_4'),
        ('NM_OP', 'OP-Saal', 'KAT_5'), ('NM_LABOR', 'Labor', 'KAT_5'),
        ('NM_NSHV', 'NSHV/Trafo', 'KAT_6'), ('NM_BATTERIE', 'Batterieladestation', 'KAT_6'),
    ]
    for nmid, nutzung, kat in nutzungsmappings:
        quelle = 'S. Veit Mail 30.05 Punkt 4' if kat == 'KAT_6' else 'Kalkulationshilfen NBG / Hilfstabellen'
        typ = 'fachexperte' if kat == 'KAT_6' else 'regel'
        statements.append(f"""
        CREATE (:NutzungsMapping {{id: '{nmid}', nutzung: '{nutzung}', kategorie: '{kat}', _quelle: '{quelle}', _typ: '{typ}', _stand: '{STAND}'}})
        """)

    # ── 18. REIFEGRAD ────────────────────────────────────────
    reifegrade = [
        ('RG_1', 'Ungeordneter Anlagenbetrieb', 1.25, 'Keine/rudimentäre Anlagendaten, erhöhter Aufwand'),
        ('RG_2', 'Reaktiver Anlagenbetrieb', 1.25, 'Teilweise Unterlagen, Nachholbedarf'),
        ('RG_3', 'Strukturierter Regelbetrieb', 1.00, 'Standardfall = 100% Basis'),
        ('RG_4', 'Hochprofessioneller Betrieb', 0.80, 'Alles vorhanden, Abschlag 15-20%'),
    ]
    for rgid, name, faktor, beschr in reifegrade:
        statements.append(f"""
        CREATE (:Reifegrad {{id: '{rgid}', name: '{name}', faktor: {faktor}, beschreibung: '{beschr}', _quelle: 'S. Veit Mail 30.05 Punkt 7', _typ: 'fachexperte', _stand: '{STAND}'}})
        """)

    # ── 19. DOKUMENTATIONSZUSCHLAG ───────────────────────────
    statements.append(f"""
    CREATE (:Dokumentationszuschlag {{id: 'DOK_STANDARD', name: 'Standard (nur bei Abweichung)', faktor: 1.0, nur_dguv: false, _quelle: 'S. Pausch Mail 29.05', _typ: 'fachexperte', _stand: '{STAND}'}})
    """)
    statements.append(f"""
    CREATE (:Dokumentationszuschlag {{id: 'DOK_VOLL', name: 'Vollerfassung Messdaten', faktor: 1.30, nur_dguv: true, _quelle: 'S. Pausch Mail 29.05 + S. Veit Mail 30.05 Punkt 6', _typ: 'fachexperte', _stand: '{STAND}'}})
    """)

    # ── 20. PREISSTEIGERUNG ──────────────────────────────────
    for jahr, steigerung in [(2020, 0.282), (2021, 0.244), (2022, 0.208), (2023, 0.148), (2024, 0.083), (2025, 0.055)]:
        statements.append(f"""
        CREATE (:Preissteigerung {{id: 'PS_{jahr}', jahr: {jahr}, steigerung_vs_2026: {steigerung}, _quelle: 'S. Veit Mail 30.05 Punkt 9', _typ: 'fachexperte', _stand: '{STAND}'}})
        """)

    # ── 21. WARNREGELN ───────────────────────────────────────
    statements.append(f"""
    CREATE (:Warnregel {{id: 'WARN_REFERENZ', schwelle_prozent: 20, text: 'Neukalkulation weicht >20% vom fortgeschriebenen Referenzpreis ab — fachliche Plausibilisierung empfohlen', _quelle: 'S. Veit Mail 30.05 Punkt 9', _typ: 'fachexperte', _stand: '{STAND}'}})
    """)
    statements.append(f"""
    CREATE (:Warnregel {{id: 'WARN_NICHT_KALKULIERBAR', text: 'Für diese Anfrage kann keine belastbare Kalkulation erstellt werden', _quelle: 'PRD v2.1 Sektion 5.3', _typ: 'regel', _stand: '{STAND}'}})
    """)

    # ── 22. REFERENZOBJEKTE (Gersthofen) ─────────────────────
    gersthofen_objekte = [
        ('REF_G01', 'Rathaus', 'Verwaltungsgebäude', '86368', 7996.00, 24),
        ('REF_G02', 'Kulturamt', 'Verwaltungsgebäude', '86368', 434.00, 1),
        ('REF_G03', 'Pestalozzischule', 'Schule', '86368', 3992.80, 10),
        ('REF_G04', 'Mozartschule', 'Schule', '86368', 2384.00, 6),
        ('REF_G06', 'Mittagsbetreuung Pestalozzischule', 'Schule', '86368', 1402.00, 4),
        ('REF_G07', 'Anna-Pröll-Mittelschule', 'Schule', '86368', 5386.00, 14),
        ('REF_G08', 'Sportbetriebsgebäude', 'Versammlungsstätte', '86368', 578.00, 2),
        ('REF_G09', 'St. Ulrich Kindertagesstätte', 'Kindergarten', '86368', 1427.20, 4),
        ('REF_G10', 'Hedwigskindergarten', 'Kindergarten', '86368', 680.00, 2),
        ('REF_G11', 'Kolpingskindergarten', 'Kindergarten', '86368', 710.00, 2),
        ('REF_G12', 'St. Elisabeth', 'Kindergarten', '86368', 2680.00, 7),
        ('REF_G13', 'Blumenwiese Kindertagesstätte', 'Kindergarten', '86368', 376.00, 1),
        ('REF_G14', 'Lechstrolche Kindertagesstätte', 'Kindergarten', '86368', 2256.40, 6),
        ('REF_G15', 'Kinderhaus am Ballonstartplatz', 'Kindergarten', '86368', 1882.80, 5),
        ('REF_G16', 'Via Claudia Kindertagesstätte', 'Kindergarten', '86368', 1350.80, 4),
        ('REF_G17', 'Kindervilla Tiefenbacher', 'Kindergarten', '86368', 2084.40, 5),
        ('REF_G18', 'Wohnanlage Pestalozzistr. 2', 'Wohngebäude', '86368', 778.40, 2),
        ('REF_G30', 'Doppelhaus Lehnholzweg 3', 'Wohngebäude', '86368', 454.40, 1),
        ('REF_G33', 'Rathaus Tiefgarage', 'Tiefgarage', '86368', 898.00, 3),
        ('REF_G34', 'GVG-Busbetriebshof', 'Industrie', '86368', 1606.00, 4),
        ('REF_G35', 'Bauhof', 'Industrie', '86368', 1344.80, 3),
        ('REF_G39', 'Jugendbegegnungsstätte', 'Versammlungsstätte', '86368', 820.00, 2),
        ('REF_G41', 'Ballonmuseum/Bücherei', 'Museum', '86368', 3627.20, 9),
        ('REF_G42', 'Musikschule', 'Schule', '86368', 950.00, 3),
        ('REF_G43', 'Kapelle St. Emmeran', 'Kirche', '86368', 392.40, 1),
    ]
    for refid, name, gtyp, plz, preis, uv in gersthofen_objekte:
        name_escaped = name.replace("'", "\\'")
        statements.append(f"""
        CREATE (:Referenzobjekt {{id: '{refid}', name: '{name_escaped}', gebaeudetyp: '{gtyp}', ort: 'Gersthofen', plz: '{plz}', gesamtpreis: {preis}, anzahl_uv: {uv}, _quelle: 'Ausschreibung Gersthofen 2025', _typ: 'ausschreibung', _stand: '{STAND}'}})
        """)

    # ── 25. TYPISCHE VERTEILUNGEN (aus 10k Prüfberichten) ────
    # UV/HV defaults per Gebäudetyp — wenn Kunde UV nicht kennt
    typische_verteilungen = [
        ('TV_KRANKENHAUS', 'Krankenhaus', 11, 12, 2, 'Krankenhaus/Klinik'),
        ('TV_HOTEL', 'Hotel', 13, 8, 2, 'Hotel/Resort'),
        ('TV_SCHULE', 'Schule', 10, 10, 1, 'Schulgebäude/Gymnasium'),
        ('TV_BUERO', 'Bürogebäude', 6, 8, 1, 'Büro/Verwaltungsgebäude'),
        ('TV_VERWALTUNG', 'Verwaltungsgebäude', 4, 4, 1, 'Rathaus/Behörde'),
        ('TV_HOCHSCHULE', 'Hochschule', 10, 12, 2, 'Universität/Hochschule'),
        ('TV_GEMEINSCH', 'Gemeinschaftsunterkunft', 5, 5, 1, 'Unterkunft/Asyl'),
        ('TV_SUPERMARKT', 'Lebensmittelmarkt', 3, 3, 1, 'Supermarkt/Discounter'),
        ('TV_KINDERGARTEN', 'Kindergarten', 3, 3, 1, 'Kita/Kindergarten'),
        ('TV_FEUERWEHR', 'Feuerwehrgerätehaus', 2, 2, 1, 'Feuerwehr/Rettungswache'),
        ('TV_BAUHOF', 'Bauhof', 6, 4, 1, 'Bauhof/Wertstoffhof'),
        ('TV_MEHRZWECK', 'Mehrzweckhalle', 8, 8, 1, 'Stadthalle/Mehrzweckhalle'),
    ]
    for tvid, gtyp, avg_uv, med_uv, avg_hv, alias in typische_verteilungen:
        statements.append(f"""
        CREATE (:TypischeVerteilung {{id: '{tvid}', gebaeudetyp: '{gtyp}', avg_uv: {avg_uv}, median_uv: {med_uv}, avg_hv: {avg_hv}, alias: '{alias}', _quelle: 'Batch Extraction 10.096 MA507 Berichte', _typ: 'statistik', _stand: '{STAND}'}})
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
