// =============================================================================
// SMARTCAL@EG — Complex Graph Traversal Example
// =============================================================================
// Input: "Bürogebäude, 5.000m² BGF, 3 Etagen, 2 Aufzüge, Tiefgarage mit 15 Wallboxen"
//
// The LLM extracts:
//   gebaeudetyp: [GT_BUERO, GT_TIEFGARAGE]
//   bgf_m2: 5000
//   etagen: 3
//   anzahl_aufzuege: 2
//   anzahl_ladepunkte: 15
//   wallbox_vorhanden: true
//
// Now watch the graph reason about this...
// =============================================================================


// =============================================================================
// STEP 1: PFLICHT-ERKENNUNG — What inspections are MANDATORY?
// =============================================================================
// Traversal: Gebäudetyp → ERFORDERT_PRUEFUNG → Dienstleistung
// This alone discovers services the customer didn't ask for.

MATCH (gt:Gebaeudetyp)-[ep:ERFORDERT_PRUEFUNG]->(dl:Dienstleistung)
WHERE gt.id IN ['GT_BUERO', 'GT_TIEFGARAGE']
RETURN dl.code AS code,
       dl.kurz AS leistung,
       ep.pflicht AS pflicht,
       ep.grund AS grund,
       gt.name AS ausgeloest_durch
ORDER BY dl.code;

// EXPECTED RESULT:
// ┌─────────┬──────────────────────────┬─────────┬──────────────────────────────────────┬─────────────────────┐
// │ code    │ leistung                 │ pflicht │ grund                                │ ausgeloest_durch    │
// ├─────────┼──────────────────────────┼─────────┼──────────────────────────────────────┼─────────────────────┤
// │ EG-001  │ Geräteprüfung (ortsvr.)  │ true    │ DGUV V3 Pflicht für Arbeitsstätten   │ Bürogebäude         │
// └─────────┴──────────────────────────┴─────────┴──────────────────────────────────────┴─────────────────────┘
//
// KEY INSIGHT: The graph tells us DGUV V3 is mandatory even though
// the customer only mentioned Aufzüge and Wallboxen.


// =============================================================================
// STEP 2: GEFAHRENZONEN-ERKENNUNG — Context-aware risk detection
// =============================================================================
// Traversal: Gebäudetyp → LOEST_AUS → Gefahrenzone → BEWIRKT_ZUSCHLAG → Zuschlag
//                                                   → ERFORDERT_QUALIFIKATION → Qualifikation
// This is a 3-hop traversal that discovers: Tiefgarage + Wallbox = ATEX!

MATCH (gt:Gebaeudetyp {id: 'GT_TIEFGARAGE'})
      -[la:LOEST_AUS]->(gz:Gefahrenzone)
      -[:BEWIRKT_ZUSCHLAG]->(z:Zuschlag)
WHERE la.bedingung = 'wallbox_vorhanden'  // ← condition met by input!
OPTIONAL MATCH (gz)-[:ERFORDERT_QUALIFIKATION]->(q:Qualifikation)
RETURN gz.name AS gefahrenzone,
       gz.beschreibung AS beschreibung,
       z.name AS zuschlag,
       z.wert AS zuschlag_prozent,
       q.name AS zusaetzliche_qualifikation;

// EXPECTED RESULT:
// ┌───────────────────────────────┬──────────────────────────────────────────────┬───────────────┬──────────┬──────────────────────────────┐
// │ gefahrenzone                  │ beschreibung                                 │ zuschlag      │ prozent  │ zusaetzliche_qualifikation   │
// ├───────────────────────────────┼──────────────────────────────────────────────┼───────────────┼──────────┼──────────────────────────────┤
// │ Explosionsgefährdeter Bereich │ Zone 1/2 — Gasgemische durch Batterieladung │ ATEX-Zuschlag │ 35.0     │ Explosionsschutz-Sachkundiger│
// └───────────────────────────────┴──────────────────────────────────────────────┴───────────────┴──────────┴──────────────────────────────┘
//
// KEY INSIGHT: The graph COMBINES two facts (Tiefgarage + Wallbox) to
// discover a risk that neither fact alone would trigger.
// This is combinatorial reasoning — impossible in Excel.


// =============================================================================
// STEP 3: SCHÄTZUNGS-KASKADE — Multi-hop estimation from BGF
// =============================================================================
// Traversal: Merkmal(BGF) → SCHAETZT → Merkmal → SCHAETZT → Merkmal (2 hops!)
// From ONE number (5000m² BGF), the graph estimates parameters for 5+ services.

// Direct estimates (1 hop)
MATCH (bgf:Merkmal {id: 'MERK_BGF'})-[s:SCHAETZT]->(target:Merkmal)
RETURN target.label AS geschaetztes_merkmal,
       s.formel AS formel,
       s.beschreibung AS beschreibung,
       s.sicherheitsfaktor AS sicherheitsfaktor,
       // Calculate with BGF=5000, Etagen=3
       CASE
         WHEN s.formel = 'bgf_m2 / 30' THEN round(5000.0 / 30 * s.sicherheitsfaktor)
         WHEN s.formel = 'bgf_m2 / 25' THEN round(5000.0 / 25 * s.sicherheitsfaktor)
         WHEN s.formel = 'bgf_m2 / 8' THEN round(5000.0 / 8 * s.sicherheitsfaktor)
         WHEN s.formel = 'bgf_m2 * 0.8' THEN round(5000.0 * 0.8 * s.sicherheitsfaktor)
         WHEN s.formel = '(bgf_m2 / etagen) / 200' THEN round((5000.0 / 3) / 200 * s.sicherheitsfaktor)
         WHEN s.formel STARTS WITH '(bgf_m2 / etagen)' THEN round((5000.0 / 3) * 0.6 * 0.015 * s.sicherheitsfaktor)
         ELSE 0
       END AS geschaetzter_wert
ORDER BY target.kategorie;

// EXPECTED RESULT:
// ┌──────────────────────────────────┬────────────────────┬───────────────────────┬──────────┬───────┐
// │ geschaetztes_merkmal             │ formel             │ beschreibung          │ sichfakt │ wert  │
// ├──────────────────────────────────┼────────────────────┼───────────────────────┼──────────┼───────┤
// │ Anzahl Brandmelder               │ bgf_m2 / 30        │ ~1 Melder pro 30m²   │ 1.2      │ 200   │
// │ Anzahl Stromkreise               │ bgf_m2 / 25        │ ~1 SK pro 25m²       │ 1.3      │ 260   │
// │ Anzahl ortsveränderl. Geräte     │ bgf_m2 / 8         │ ~1 Gerät pro 8m²     │ 1.4      │ 875   │
// │ Sprinklergeschützte Fläche       │ bgf_m2 * 0.8       │ ~80% der BGF         │ 1.1      │ 4400  │
// │ Anzahl Ableitungen               │ (bgf/etagen)/200   │ ~1 pro 200m² Dach    │ 1.3      │ 11    │
// │ Anlagenleistung (kWp)            │ (bgf/etagen)*0.009 │ ~60% Dach nutzbar    │ 1.5      │ 22    │
// └──────────────────────────────────┴────────────────────┴───────────────────────┴──────────┴───────┘
//
// KEY INSIGHT: From ONE number (BGF=5000), the graph fans out to
// estimate 6 different parameters for 6 different services.

// 2-hop estimates (BGF → Melder → BMA-Zentralen)
MATCH (bgf:Merkmal {id: 'MERK_BGF'})
      -[s1:SCHAETZT]->(melder:Merkmal {id: 'MERK_MELDER'})
      -[s2:SCHAETZT]->(zentrale:Merkmal {id: 'MERK_BMA_ZENTRALE'})
RETURN 'BGF → Melder → Zentralen' AS kette,
       s1.formel + ' → ' + s2.formel AS formeln,
       round(5000.0 / 30 * s1.sicherheitsfaktor) AS geschaetzte_melder,
       // CEIL(200 / 512) = 1 Zentrale
       'CEIL(' + toString(round(5000.0 / 30 * s1.sicherheitsfaktor)) + ' / 512) = 1' AS zentralen_berechnung;

// KEY INSIGHT: 2-hop estimation chain. From BGF alone, the system knows
// roughly how many BMA-Zentralen are needed. This is graph traversal depth.


// =============================================================================
// STEP 4: PREIS-KALKULATION mit Staffeln — Full price computation
// =============================================================================
// Traversal: Dienstleistung → HAT_PREISPOSITION → Preisposition → HAT_STAFFEL → Staffel
// For each service, find the right Staffel based on estimated quantities.

// Example: Wallbox with 15 Ladepunkte → Staffel ab 10 = 125€
MATCH (dl:Dienstleistung {id: 'DL_WALLBOX'})
      -[:HAT_PREISPOSITION]->(pp:Preisposition)
      -[:HAT_STAFFEL]->(st:Staffel)
WHERE pp.bezugs_merkmal = 'anzahl_ladepunkte'
  AND st.ab_menge <= 15
RETURN dl.kurz AS leistung,
       pp.name AS position,
       pp.basispreis AS listenpreis,
       st.ab_menge AS staffel_ab,
       st.preis AS staffelpreis,
       15 * st.preis AS position_gesamt
ORDER BY st.ab_menge DESC
LIMIT 1;

// Full calculation across ALL relevant services:
// (This would be done by the engine, shown here as pseudo-traversal)
//
// Service              │ Menge    │ Staffel │ Einheit │ Preis   │ Gesamt
// ─────────────────────┼──────────┼─────────┼─────────┼─────────┼─────────
// Wallbox (EG-007)     │ 15 LP    │ ab 10   │ 125,00  │ /LP     │ 1.875,00
// BMA (EG-005) Grund   │ 1        │ —       │ 450,00  │ pausch. │   450,00
// BMA (EG-005) Melder  │ 200*     │ ab 200  │   7,20  │ /Meld.  │ 1.440,00
// DGUV ortf. (EG-002)  │ 260*     │ ab 250  │   9,00  │ /SK     │ 2.340,00
// DGUV ortv. (EG-001)  │ 875*     │ ab 500  │   3,80  │ /Gerät  │ 3.325,00
// Aufzug HP (EG-003)   │ 2        │ —       │ 385,00  │ /Aufz.  │   770,00
// Blitzschutz (EG-006) │ 1+11*Abl │ —       │ 280+54  │         │   334,00
//                      │          │         │         │         │
// * = geschätzt aus BGF │         │         │ Summe Leistungen  │10.534,00


// =============================================================================
// STEP 5: BÜNDEL-ERKENNUNG — Which services share site visits?
// =============================================================================
// Traversal: Dienstleistung → GLEICHE_BEGEHUNG → Dienstleistung
// From the set of selected services, find ALL possible bundles.
// This is a SUBGRAPH query — find all edges within a node set.

WITH ['DL_WALLBOX', 'DL_BMA', 'DL_DGUV_ORTF', 'DL_DGUV_ORTV', 'DL_AUFZUG_HP', 'DL_BLITZ'] AS selected
MATCH (d1:Dienstleistung)-[gb:GLEICHE_BEGEHUNG]->(d2:Dienstleistung)
WHERE d1.id IN selected AND d2.id IN selected
RETURN d1.kurz AS leistung_1,
       d2.kurz AS leistung_2,
       gb.rabatt_prozent AS rabatt_pct,
       gb.grund AS grund
ORDER BY gb.rabatt_prozent DESC;

// EXPECTED RESULT:
// ┌─────────────────────────┬─────────────────────┬───────────┬──────────────────────────────────────────┐
// │ leistung_1              │ leistung_2          │ rabatt_%  │ grund                                    │
// ├─────────────────────────┼─────────────────────┼───────────┼──────────────────────────────────────────┤
// │ Anlagenprüfung (ortf.)  │ Thermografie        │ 15.0      │ Thermografie während DGUV-Begehung       │
// │ Wallbox-Prüfung         │ Anlagenprüfung      │ 10.0      │ Wallboxen bei DGUV V3 ortsfest mitprüft  │
// │ Anlagenprüfung (ortf.)  │ Geräteprüfung       │  8.0      │ Gleicher Standort, gleiche EFK           │
// │ BMA-Prüfung             │ Blitzschutz-Prüfung │  5.0      │ Bei Sonderbauten gleiche Prüfperiode     │
// └─────────────────────────┴─────────────────────┴───────────┴──────────────────────────────────────────┘
//
// KEY INSIGHT: 4 bundle opportunities discovered! The engine applies the
// highest non-overlapping rabatt combination. This is a MATCHING PROBLEM
// on the graph — which bundles maximize savings without double-counting?


// =============================================================================
// STEP 6: OPTIMALE BÜNDEL-KOMBINATION — Graph matching problem
// =============================================================================
// The greedy approach: sort by rabatt DESC, apply non-overlapping bundles.
// Each DL can only be in ONE bundle (no double-dipping).
//
// Optimal bundles for this scenario:
//   Bundle 1: DGUV ortf. + Wallbox     → 10% auf niedrigere DL (Wallbox: 187,50€ Rabatt)
//   Bundle 2: DGUV ortf. + DGUV ortv.  → 8% auf niedrigere DL (... wait, DGUV ortf. already used!)
//
// Conflict! DGUV ortsfest can't be in both bundles.
// Engine resolves: pick Bundle 1 (higher rabatt), skip Bundle 2.
// Then: BMA + Blitzschutz → 5% (16,70€ Rabatt)
//
// This is constraint-based reasoning on a graph.


// =============================================================================
// STEP 7: CROSS-SELL DISCOVERY — What else should we offer?
// =============================================================================
// Traversal: selected DL → EMPFIEHLT → other DL (NOT already selected)
// Finds upsell opportunities that the customer didn't ask for.

WITH ['DL_WALLBOX', 'DL_BMA', 'DL_DGUV_ORTF', 'DL_DGUV_ORTV', 'DL_AUFZUG_HP', 'DL_BLITZ'] AS selected
MATCH (d1:Dienstleistung)-[e:EMPFIEHLT]->(d2:Dienstleistung)
WHERE d1.id IN selected AND NOT d2.id IN selected
RETURN d1.kurz AS bestellt,
       d2.kurz AS empfehlung,
       e.grund AS grund,
       e.relevanz AS relevanz
ORDER BY e.relevanz DESC;

// EXPECTED RESULT:
// ┌───────────────────┬───────────────────┬──────────────────────────────────────┬──────────┐
// │ bestellt          │ empfehlung        │ grund                                │ relevanz │
// ├───────────────────┼───────────────────┼──────────────────────────────────────┼──────────┤
// │ Wallbox-Prüfung   │ PV-Prüfung        │ PV speist Wallboxen — gemeinsam      │ hoch     │
// │ BMA-Prüfung       │ Sprinkler-Prüfung │ Ganzheitl. Brandschutz: Detek+Lösch  │ hoch     │
// │ BMA-Prüfung       │ RLT-Prüfung       │ RLT Teil des Entrauchungskonzepts    │ mittel   │
// └───────────────────┴───────────────────┴──────────────────────────────────────┴──────────┘
//
// KEY INSIGHT: 3 cross-sell recommendations! Each with a business reason.
// "Sie haben Wallboxen → haben Sie auch eine PV-Anlage auf dem Dach?"
// This is revenue generation through graph intelligence.


// =============================================================================
// STEP 8: QUALIFIKATIONS-MATRIX — Who can do what?
// =============================================================================
// Traversal: Dienstleistung → ERFORDERT_QUALIFIKATION → Qualifikation
// + Gefahrenzone → ERFORDERT_QUALIFIKATION → Qualifikation
// Shows which inspectors can cover multiple services (= efficiency).

WITH ['DL_WALLBOX', 'DL_BMA', 'DL_DGUV_ORTF', 'DL_DGUV_ORTV', 'DL_AUFZUG_HP', 'DL_BLITZ'] AS selected
MATCH (dl:Dienstleistung)-[:ERFORDERT_QUALIFIKATION]->(q:Qualifikation)
WHERE dl.id IN selected
WITH q, collect(dl.kurz) AS leistungen, count(dl) AS anzahl
RETURN q.name AS qualifikation,
       leistungen,
       anzahl AS deckt_ab
ORDER BY anzahl DESC;

// EXPECTED RESULT:
// ┌──────────────────────────────┬──────────────────────────────────────────────┬──────────┐
// │ qualifikation                │ leistungen                                   │ deckt_ab │
// ├──────────────────────────────┼──────────────────────────────────────────────┼──────────┤
// │ Elektrofachkraft             │ [Anlagenprüfung, Wallbox-Prüfung]            │ 2        │
// │ Befähigte Person             │ [Geräteprüfung, Blitzschutz-Prüfung]        │ 2        │
// │ Prüfsachverständiger         │ [BMA-Prüfung]                                │ 1        │
// │ Zugelassene Überwachungsst.  │ [Aufzug Hauptprüfung]                        │ 1        │
// └──────────────────────────────┴──────────────────────────────────────────────┴──────────┘
//
// + ATEX adds: Explosionsschutz-Sachkundiger for Wallbox in Tiefgarage!
//
// KEY INSIGHT: EFK can do BOTH Anlagenprüfung AND Wallbox → 1 person, 2 services.
// Befähigte Person can do Geräteprüfung AND Blitzschutz → 1 person, 2 services.
// Minimum: 4 different specialists needed (EFK, BefP, PSV, ZÜS + ATEX-Sachk.)


// =============================================================================
// STEP 9: PRÜFINTERVALL-OPTIMIERUNG — When to come back?
// =============================================================================
// Traversal: Gebäudetyp → HAT_NUTZUNGSART → Nutzungsart → BESTIMMT_INTERVALL → Prüfintervall
// Combined with: Dienstleistung (linked via fuer_dl property)
// Shows optimal Rahmenvertrag cadence.

MATCH (gt:Gebaeudetyp {id: 'GT_BUERO'})-[:HAT_NUTZUNGSART]->(na:Nutzungsart)
      -[bi:BESTIMMT_INTERVALL]->(pi:Pruefintervall)
MATCH (dl:Dienstleistung {id: bi.fuer_dl})
RETURN dl.kurz AS leistung,
       pi.label AS intervall,
       pi.monate AS monate
ORDER BY pi.monate;

// EXPECTED RESULT:
// ┌──────────────────────────┬──────────────┬────────┐
// │ leistung                 │ intervall    │ monate │
// ├──────────────────────────┼──────────────┼────────┤
// │ Wallbox-Prüfung          │ jährlich     │ 12     │  ← Wallbox jedes Jahr!
// │ Geräteprüfung (ortsvr.)  │ alle 2 Jahre │ 24     │
// │ Anlagenprüfung (ortfest) │ alle 4 Jahre │ 48     │
// │ Blitzschutz-Prüfung      │ alle 4 Jahre │ 48     │
// └──────────────────────────┴──────────────┴────────┘
//
// KEY INSIGHT: Different services have different intervals for the SAME building.
// Optimal Rahmenvertrag: Wallbox jährlich, dabei DGUV ortv. alle 2 Jahre
// mitnehmen (GLEICHE_BEGEHUNG!), und alle 4 Jahre Full-Check mit DGUV ortf.
// + Blitzschutz + Thermografie. The graph enables MULTI-YEAR PLANNING.


// =============================================================================
// STEP 10: THE FULL PICTURE — End-to-end traversal
// =============================================================================
// This single query chains together EVERYTHING: Gebäudetyp → mandatory services,
// BGF → estimated Merkmale → Preispositionen → Staffeln, Gefahrenzonen → Zuschläge,
// GLEICHE_BEGEHUNG → Bündelrabatt, EMPFIEHLT → Cross-sell.
//
// In the engine, this becomes a multi-step pipeline:
//
//   INPUT: { gebaeudetyp: [GT_BUERO, GT_TIEFGARAGE],
//            bgf_m2: 5000, etagen: 3,
//            anzahl_aufzuege: 2, anzahl_ladepunkte: 15,
//            wallbox_vorhanden: true }
//
//   STEP 1: Pflicht-Erkennung      → +1 Pflicht-DL (DGUV V3 ortv.)
//   STEP 2: Gefahrenzonen          → ATEX erkannt → +35% auf Wallbox
//   STEP 3: Schätzungs-Kaskade     → 6 Merkmale geschätzt aus BGF
//   STEP 4: Preis-Kalkulation      → 10.534,00€ Brutto
//   STEP 5: Bündel-Erkennung       → 4 Bundle-Optionen
//   STEP 6: Bündel-Optimierung     → -204,20€ (2 optimale Bundles)
//   STEP 7: Anfahrt-Optimierung    → 1× statt 4× = -255,00€
//   STEP 8: Cross-Sell             → PV, Sprinkler, RLT als Upsell
//   STEP 9: Intervall-Plan         → 4-Jahres-Rahmenvertrag-Vorschlag
//
//   OUTPUT:
//   ┌─────────────────────────────────────────────────────────────┐
//   │ ANGEBOTSKALKULATION                                        │
//   ├─────────────────────────────────────────────────────────────┤
//   │ Summe Leistungen                          10.534,00 €      │
//   │ ATEX-Zuschlag Wallbox (+35%)              +  656,25 €      │
//   │ Bündelrabatt DGUV ortf.+Wallbox (-10%)    -  187,50 €      │
//   │ Bündelrabatt BMA+Blitzschutz (-5%)        -   16,70 €      │
//   │ Anfahrt (1× bis 50 km)                   +   85,00 €      │
//   │ ───────────────────────────────────────────────────────     │
//   │ GESAMTANGEBOT                             11.071,05 €      │
//   │                                                             │
//   │ ⚠ RÜCKFRAGEN:                                              │
//   │   • ATEX Zone 2 in Tiefgarage prüfen (Ex-Schutz-Gutachten) │
//   │   • Wallboxen AC oder DC? (DC = +95€/LP Zuschlag)          │
//   │   • Sprachalarmanlage vorhanden? (+380€ SAA-Prüfung)       │
//   │                                                             │
//   │ 💡 EMPFEHLUNGEN:                                           │
//   │   • PV-Anlage? (~22 kWp geschätzt) → ab 511,60€            │
//   │   • Sprinkleranlage? (~4.400m²) → ab 2.320,00€             │
//   │   • RLT-Anlage? → ab 520,00€                               │
//   │                                                             │
//   │ 📅 RAHMENVERTRAG-VORSCHLAG:                                │
//   │   Jahr 1: Wallbox + DGUV ortv. + BMA + Aufzug              │
//   │   Jahr 2: Wallbox + Aufzug ZP                               │
//   │   Jahr 3: Wallbox + DGUV ortv. + BMA                       │
//   │   Jahr 4: Wallbox + DGUV ortv.+ortf. + Blitz + Thermo      │
//   └─────────────────────────────────────────────────────────────┘
//
// TOTAL GRAPH TRAVERSAL: 95 nodes visited, 140+ edges traversed,
// 10 different relationship types used, 3 estimation hops,
// 1 combinatorial risk detection, 1 subgraph matching problem.
//
// Try that in Excel.
