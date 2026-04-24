// =============================================================================
// SMARTCAL@EG — Knowledge Graph Schema
// =============================================================================
// Graph name: "smartcal" (separate from MH "hvac" graph)
//
// This is NOT a tree — it's a rich graph with cross-cutting relationships:
//   - Merkmale shared across services (BGF → estimates for BMA, DGUV, Sprinkler)
//   - Normen shared across services (BetrSichV governs Aufzüge AND Druckgeräte)
//   - Gebäudetyp triggers context-aware rules (Tiefgarage + Wallbox = ATEX)
//   - Bundle detection via GLEICHE_BEGEHUNG relationships
//   - Qualifikationen shared across services
// =============================================================================


// =============================================================================
// CONSTRAINTS
// =============================================================================
CREATE CONSTRAINT IF NOT EXISTS FOR (d:Dienstleistung) REQUIRE d.id IS UNIQUE;
CREATE CONSTRAINT IF NOT EXISTS FOR (m:Merkmal) REQUIRE m.id IS UNIQUE;
CREATE CONSTRAINT IF NOT EXISTS FOR (p:Preisposition) REQUIRE p.id IS UNIQUE;
CREATE CONSTRAINT IF NOT EXISTS FOR (s:Staffel) REQUIRE s.id IS UNIQUE;
CREATE CONSTRAINT IF NOT EXISTS FOR (n:Norm) REQUIRE n.id IS UNIQUE;
CREATE CONSTRAINT IF NOT EXISTS FOR (q:Qualifikation) REQUIRE q.id IS UNIQUE;
CREATE CONSTRAINT IF NOT EXISTS FOR (g:Gebaeudetyp) REQUIRE g.id IS UNIQUE;
CREATE CONSTRAINT IF NOT EXISTS FOR (z:Zuschlag) REQUIRE z.id IS UNIQUE;
CREATE CONSTRAINT IF NOT EXISTS FOR (r:Region) REQUIRE r.id IS UNIQUE;
CREATE CONSTRAINT IF NOT EXISTS FOR (gz:Gefahrenzone) REQUIRE gz.id IS UNIQUE;
CREATE CONSTRAINT IF NOT EXISTS FOR (pi:Pruefintervall) REQUIRE pi.id IS UNIQUE;
CREATE CONSTRAINT IF NOT EXISTS FOR (na:Nutzungsart) REQUIRE na.id IS UNIQUE;


// =============================================================================
// NORMEN (Regulations) — shared across multiple services
// =============================================================================

MERGE (n_dguv3:Norm {id: 'NORM_DGUV3'})
SET n_dguv3.name = 'DGUV Vorschrift 3',
    n_dguv3.scope = 'Elektrische Anlagen und Betriebsmittel',
    n_dguv3.herausgeber = 'Deutsche Gesetzliche Unfallversicherung';

MERGE (n_betrsichv:Norm {id: 'NORM_BETRSICHV'})
SET n_betrsichv.name = 'Betriebssicherheitsverordnung (BetrSichV)',
    n_betrsichv.scope = 'Überwachungsbedürftige Anlagen',
    n_betrsichv.herausgeber = 'Bundesministerium für Arbeit und Soziales';

MERGE (n_vde0100:Norm {id: 'NORM_VDE0100'})
SET n_vde0100.name = 'DIN VDE 0100-600',
    n_vde0100.scope = 'Erstprüfung elektrischer Anlagen';

MERGE (n_vde0105:Norm {id: 'NORM_VDE0105'})
SET n_vde0105.name = 'DIN VDE 0105-100',
    n_vde0105.scope = 'Wiederkehrende Prüfung elektrischer Anlagen';

MERGE (n_din14675:Norm {id: 'NORM_DIN14675'})
SET n_din14675.name = 'DIN 14675',
    n_din14675.scope = 'Brandmeldeanlagen — Aufbau und Betrieb';

MERGE (n_vde0833:Norm {id: 'NORM_VDE0833'})
SET n_vde0833.name = 'DIN VDE 0833',
    n_vde0833.scope = 'Gefahrenmeldeanlagen für Brand, Einbruch, Überfall';

MERGE (n_din62305:Norm {id: 'NORM_DIN62305'})
SET n_din62305.name = 'DIN EN 62305 (VDE 0185)',
    n_din62305.scope = 'Blitzschutzsysteme';

MERGE (n_lbo:Norm {id: 'NORM_LBO'})
SET n_lbo.name = 'Landesbauordnung (LBO)',
    n_lbo.scope = 'Bauordnungsrecht — Prüfpflichten für Sonderbauten';

MERGE (n_atex:Norm {id: 'NORM_ATEX'})
SET n_atex.name = 'ATEX-Richtlinie 2014/34/EU',
    n_atex.scope = 'Explosionsschutz in gefährdeten Bereichen';

MERGE (n_vds_cea:Norm {id: 'NORM_VDS_CEA'})
SET n_vds_cea.name = 'VdS CEA 4001',
    n_vds_cea.scope = 'Sprinkleranlagen — Planung und Einbau';

MERGE (n_din18232:Norm {id: 'NORM_DIN18232'})
SET n_din18232.name = 'DIN 18232',
    n_din18232.scope = 'Rauch- und Wärmefreihaltung';


// =============================================================================
// QUALIFIKATIONEN — shared across services (creates cross-links)
// =============================================================================

MERGE (q_efk:Qualifikation {id: 'QUAL_EFK'})
SET q_efk.name = 'Elektrofachkraft',
    q_efk.beschreibung = 'Nach DIN VDE 1000-10 befähigte Person';

MERGE (q_psv:Qualifikation {id: 'QUAL_PSV'})
SET q_psv.name = 'Prüfsachverständiger',
    q_psv.beschreibung = 'Staatlich anerkannt nach Landesbauordnung';

MERGE (q_zues:Qualifikation {id: 'QUAL_ZUES'})
SET q_zues.name = 'Zugelassene Überwachungsstelle (ZÜS)',
    q_zues.beschreibung = 'Akkreditiert nach BetrSichV für überwachungsbedürftige Anlagen';

MERGE (q_befp:Qualifikation {id: 'QUAL_BEFP'})
SET q_befp.name = 'Befähigte Person',
    q_befp.beschreibung = 'Nach TRBS 1203 für Prüfung befähigt';

MERGE (q_thermo:Qualifikation {id: 'QUAL_THERMO'})
SET q_thermo.name = 'Thermografie-Zertifizierung Stufe 2',
    q_thermo.beschreibung = 'DIN EN ISO 9712 Stufe 2 Thermografie';

MERGE (q_atex:Qualifikation {id: 'QUAL_ATEX'})
SET q_atex.name = 'Explosionsschutz-Sachkundiger',
    q_atex.beschreibung = 'Befähigt zur Prüfung in Ex-Bereichen';


// =============================================================================
// MERKMALE (Characteristics) — the graph's fan-out power
// =============================================================================
// Key insight: BGF connects to MULTIPLE services via SCHAETZT relationships
// This is what makes it a graph, not a tree.

// --- Gebäude-Merkmale (shared across services) ---
MERGE (m_bgf:Merkmal {id: 'MERK_BGF'})
SET m_bgf.key = 'bgf_m2',
    m_bgf.label = 'Bruttogrundfläche (BGF)',
    m_bgf.einheit = 'm²',
    m_bgf.typ = 'number',
    m_bgf.kategorie = 'gebaeude',
    m_bgf.required_at = 'grob',
    m_bgf.help_text = 'Gesamtfläche des Gebäudes inkl. aller Geschosse';

MERGE (m_etagen:Merkmal {id: 'MERK_ETAGEN'})
SET m_etagen.key = 'etagen',
    m_etagen.label = 'Anzahl Etagen/Geschosse',
    m_etagen.einheit = 'Stück',
    m_etagen.typ = 'number',
    m_etagen.kategorie = 'gebaeude',
    m_etagen.required_at = 'grob';

MERGE (m_baujahr:Merkmal {id: 'MERK_BAUJAHR'})
SET m_baujahr.key = 'baujahr',
    m_baujahr.label = 'Baujahr des Gebäudes',
    m_baujahr.einheit = 'Jahr',
    m_baujahr.typ = 'number',
    m_baujahr.kategorie = 'gebaeude',
    m_baujahr.required_at = 'mittel';

MERGE (m_standorte:Merkmal {id: 'MERK_STANDORTE'})
SET m_standorte.key = 'anzahl_standorte',
    m_standorte.label = 'Anzahl Standorte',
    m_standorte.einheit = 'Stück',
    m_standorte.typ = 'number',
    m_standorte.kategorie = 'vertrag',
    m_standorte.required_at = 'grob';

// --- DGUV V3 Merkmale ---
MERGE (m_geraete:Merkmal {id: 'MERK_GERAETE'})
SET m_geraete.key = 'anzahl_geraete',
    m_geraete.label = 'Anzahl ortsveränderliche Geräte',
    m_geraete.einheit = 'Stück',
    m_geraete.typ = 'number',
    m_geraete.kategorie = 'dguv_ortv',
    m_geraete.required_at = 'mittel';

MERGE (m_stromkreise:Merkmal {id: 'MERK_STROMKREISE'})
SET m_stromkreise.key = 'anzahl_stromkreise',
    m_stromkreise.label = 'Anzahl Stromkreise',
    m_stromkreise.einheit = 'Stück',
    m_stromkreise.typ = 'number',
    m_stromkreise.kategorie = 'dguv_ortf',
    m_stromkreise.required_at = 'mittel';

MERGE (m_schaltanlagen:Merkmal {id: 'MERK_SCHALTANLAGEN'})
SET m_schaltanlagen.key = 'anzahl_schaltanlagen',
    m_schaltanlagen.label = 'Anzahl Schaltanlagen/Verteilungen',
    m_schaltanlagen.einheit = 'Stück',
    m_schaltanlagen.typ = 'number',
    m_schaltanlagen.kategorie = 'dguv_ortf',
    m_schaltanlagen.required_at = 'fein';

MERGE (m_anlagenalter:Merkmal {id: 'MERK_ANLAGENALTER'})
SET m_anlagenalter.key = 'anlagenalter_jahre',
    m_anlagenalter.label = 'Alter der elektrischen Anlage',
    m_anlagenalter.einheit = 'Jahre',
    m_anlagenalter.typ = 'number',
    m_anlagenalter.kategorie = 'dguv_ortf',
    m_anlagenalter.required_at = 'fein';

// --- BMA Merkmale ---
MERGE (m_melder:Merkmal {id: 'MERK_MELDER'})
SET m_melder.key = 'anzahl_melder',
    m_melder.label = 'Anzahl Brandmelder',
    m_melder.einheit = 'Stück',
    m_melder.typ = 'number',
    m_melder.kategorie = 'bma',
    m_melder.required_at = 'mittel';

MERGE (m_melder_typ:Merkmal {id: 'MERK_MELDER_TYP'})
SET m_melder_typ.key = 'melder_typ',
    m_melder_typ.label = 'Meldertyp (Rauch/Hand/Wärme/Ansaug)',
    m_melder_typ.einheit = 'Auswahl',
    m_melder_typ.typ = 'multi_select',
    m_melder_typ.optionen = 'Rauchmelder,Handfeuermelder,Wärmemelder,Ansaugrauchmelder,Flammenmelder',
    m_melder_typ.kategorie = 'bma',
    m_melder_typ.required_at = 'fein';

MERGE (m_bma_zentrale:Merkmal {id: 'MERK_BMA_ZENTRALE'})
SET m_bma_zentrale.key = 'bma_zentralen',
    m_bma_zentrale.label = 'Anzahl Brandmeldezentralen',
    m_bma_zentrale.einheit = 'Stück',
    m_bma_zentrale.typ = 'number',
    m_bma_zentrale.kategorie = 'bma',
    m_bma_zentrale.required_at = 'fein';

MERGE (m_saa:Merkmal {id: 'MERK_SAA'})
SET m_saa.key = 'hat_sprachalarm',
    m_saa.label = 'Sprachalarmanlage (SAA) vorhanden?',
    m_saa.typ = 'boolean',
    m_saa.kategorie = 'bma',
    m_saa.required_at = 'mittel';

// --- Wallbox/Ladesäulen Merkmale ---
MERGE (m_ladepunkte:Merkmal {id: 'MERK_LADEPUNKTE'})
SET m_ladepunkte.key = 'anzahl_ladepunkte',
    m_ladepunkte.label = 'Anzahl Ladepunkte',
    m_ladepunkte.einheit = 'Stück',
    m_ladepunkte.typ = 'number',
    m_ladepunkte.kategorie = 'wallbox',
    m_ladepunkte.required_at = 'grob';

MERGE (m_ladetyp:Merkmal {id: 'MERK_LADETYP'})
SET m_ladetyp.key = 'ladetyp',
    m_ladetyp.label = 'Ladetyp (AC/DC)',
    m_ladetyp.typ = 'select',
    m_ladetyp.optionen = 'AC (bis 22 kW),DC (ab 50 kW),Gemischt',
    m_ladetyp.kategorie = 'wallbox',
    m_ladetyp.required_at = 'mittel';

MERGE (m_ladeleistung:Merkmal {id: 'MERK_LADELEISTUNG'})
SET m_ladeleistung.key = 'ladeleistung_kw',
    m_ladeleistung.label = 'Ladeleistung pro Punkt',
    m_ladeleistung.einheit = 'kW',
    m_ladeleistung.typ = 'number',
    m_ladeleistung.kategorie = 'wallbox',
    m_ladeleistung.required_at = 'fein';

// --- Aufzug Merkmale ---
MERGE (m_aufzuege:Merkmal {id: 'MERK_AUFZUEGE'})
SET m_aufzuege.key = 'anzahl_aufzuege',
    m_aufzuege.label = 'Anzahl Aufzüge',
    m_aufzuege.einheit = 'Stück',
    m_aufzuege.typ = 'number',
    m_aufzuege.kategorie = 'aufzug',
    m_aufzuege.required_at = 'grob';

MERGE (m_aufzugtyp:Merkmal {id: 'MERK_AUFZUGTYP'})
SET m_aufzugtyp.key = 'aufzugtyp',
    m_aufzugtyp.label = 'Aufzugstyp',
    m_aufzugtyp.typ = 'select',
    m_aufzugtyp.optionen = 'Personenaufzug,Lastenaufzug,Behindertenaufzug,Feuerwehraufzug,Autoaufzug',
    m_aufzugtyp.kategorie = 'aufzug',
    m_aufzugtyp.required_at = 'mittel';

MERGE (m_haltestellen:Merkmal {id: 'MERK_HALTESTELLEN'})
SET m_haltestellen.key = 'anzahl_haltestellen',
    m_haltestellen.label = 'Anzahl Haltestellen pro Aufzug',
    m_haltestellen.einheit = 'Stück',
    m_haltestellen.typ = 'number',
    m_haltestellen.kategorie = 'aufzug',
    m_haltestellen.required_at = 'mittel';

MERGE (m_traglast:Merkmal {id: 'MERK_TRAGLAST'})
SET m_traglast.key = 'traglast_kg',
    m_traglast.label = 'Traglast',
    m_traglast.einheit = 'kg',
    m_traglast.typ = 'number',
    m_traglast.kategorie = 'aufzug',
    m_traglast.required_at = 'fein';

// --- Blitzschutz Merkmale ---
MERGE (m_ableitungen:Merkmal {id: 'MERK_ABLEITUNGEN'})
SET m_ableitungen.key = 'anzahl_ableitungen',
    m_ableitungen.label = 'Anzahl Ableitungen',
    m_ableitungen.einheit = 'Stück',
    m_ableitungen.typ = 'number',
    m_ableitungen.kategorie = 'blitzschutz',
    m_ableitungen.required_at = 'mittel';

MERGE (m_blitzschutzklasse:Merkmal {id: 'MERK_BLITZSCHUTZKLASSE'})
SET m_blitzschutzklasse.key = 'blitzschutzklasse',
    m_blitzschutzklasse.label = 'Blitzschutzklasse',
    m_blitzschutzklasse.typ = 'select',
    m_blitzschutzklasse.optionen = 'I,II,III,IV',
    m_blitzschutzklasse.kategorie = 'blitzschutz',
    m_blitzschutzklasse.required_at = 'fein';

// --- Sprinkler Merkmale ---
MERGE (m_sprinklerflaeche:Merkmal {id: 'MERK_SPRINKLERFLAECHE'})
SET m_sprinklerflaeche.key = 'sprinklerflaeche_m2',
    m_sprinklerflaeche.label = 'Sprinklergeschützte Fläche',
    m_sprinklerflaeche.einheit = 'm²',
    m_sprinklerflaeche.typ = 'number',
    m_sprinklerflaeche.kategorie = 'sprinkler',
    m_sprinklerflaeche.required_at = 'mittel';

MERGE (m_sprinklertyp:Merkmal {id: 'MERK_SPRINKLERTYP'})
SET m_sprinklertyp.key = 'sprinklertyp',
    m_sprinklertyp.label = 'Sprinkleranlage Typ',
    m_sprinklertyp.typ = 'select',
    m_sprinklertyp.optionen = 'Nassanlage,Trockenanlage,Vorgesteuerte Anlage,Schaum-Wasser',
    m_sprinklertyp.kategorie = 'sprinkler',
    m_sprinklertyp.required_at = 'fein';

// --- PV Merkmale ---
MERGE (m_kwp:Merkmal {id: 'MERK_KWP'})
SET m_kwp.key = 'kwp',
    m_kwp.label = 'Anlagenleistung',
    m_kwp.einheit = 'kWp',
    m_kwp.typ = 'number',
    m_kwp.kategorie = 'pv',
    m_kwp.required_at = 'grob';

MERGE (m_module:Merkmal {id: 'MERK_MODULE'})
SET m_module.key = 'anzahl_module',
    m_module.label = 'Anzahl PV-Module',
    m_module.einheit = 'Stück',
    m_module.typ = 'number',
    m_module.kategorie = 'pv',
    m_module.required_at = 'mittel';

// --- Shared/Logistik Merkmale ---
MERGE (m_entfernung:Merkmal {id: 'MERK_ENTFERNUNG'})
SET m_entfernung.key = 'entfernung_km',
    m_entfernung.label = 'Entfernung zum Standort',
    m_entfernung.einheit = 'km',
    m_entfernung.typ = 'number',
    m_entfernung.kategorie = 'logistik',
    m_entfernung.required_at = 'grob';


// =============================================================================
// SCHÄTZREGELN (Estimation chains) — THIS IS THE GRAPH POWER
// =============================================================================
// BGF is the "hub" — from one number, the system estimates parameters
// for 5+ different services. This fan-out is impossible in flat Excel.

// BGF → schätzt Anzahl Melder (BMA): ~1 Melder pro 30m²
MATCH (m1:Merkmal {id: 'MERK_BGF'}), (m2:Merkmal {id: 'MERK_MELDER'})
MERGE (m1)-[:SCHAETZT {
    formel: 'bgf_m2 / 30',
    beschreibung: '~1 Melder pro 30m² Grundfläche',
    sicherheitsfaktor: 1.2,
    genauigkeit: 'grob'
}]->(m2);

// BGF → schätzt Stromkreise (DGUV V3): ~1 Stromkreis pro 25m²
MATCH (m1:Merkmal {id: 'MERK_BGF'}), (m2:Merkmal {id: 'MERK_STROMKREISE'})
MERGE (m1)-[:SCHAETZT {
    formel: 'bgf_m2 / 25',
    beschreibung: '~1 Stromkreis pro 25m² Bürofläche',
    sicherheitsfaktor: 1.3,
    genauigkeit: 'grob'
}]->(m2);

// BGF → schätzt ortsveränderliche Geräte: ~1 Gerät pro 8m²
MATCH (m1:Merkmal {id: 'MERK_BGF'}), (m2:Merkmal {id: 'MERK_GERAETE'})
MERGE (m1)-[:SCHAETZT {
    formel: 'bgf_m2 / 8',
    beschreibung: '~1 ortsveränderliches Gerät pro 8m² Bürofläche',
    sicherheitsfaktor: 1.4,
    genauigkeit: 'grob'
}]->(m2);

// BGF → schätzt Sprinklerfläche: ~80% der BGF
MATCH (m1:Merkmal {id: 'MERK_BGF'}), (m2:Merkmal {id: 'MERK_SPRINKLERFLAECHE'})
MERGE (m1)-[:SCHAETZT {
    formel: 'bgf_m2 * 0.8',
    beschreibung: '~80% der BGF ist sprinklergeschützt',
    sicherheitsfaktor: 1.1,
    genauigkeit: 'grob'
}]->(m2);

// BGF → schätzt Ableitungen (Blitzschutz): ~1 pro 200m² Dachfläche
MATCH (m1:Merkmal {id: 'MERK_BGF'}), (m2:Merkmal {id: 'MERK_ABLEITUNGEN'})
MERGE (m1)-[:SCHAETZT {
    formel: '(bgf_m2 / etagen) / 200',
    beschreibung: '~1 Ableitung pro 200m² Dachfläche (BGF/Etagen)',
    sicherheitsfaktor: 1.3,
    abhaengig_von: 'MERK_ETAGEN',
    genauigkeit: 'grob'
}]->(m2);

// Etagen → schätzt Haltestellen (Aufzug): Haltestellen = Etagen + 1 (EG+OGs+UG)
MATCH (m1:Merkmal {id: 'MERK_ETAGEN'}), (m2:Merkmal {id: 'MERK_HALTESTELLEN'})
MERGE (m1)-[:SCHAETZT {
    formel: 'etagen + 1',
    beschreibung: 'Haltestellen ≈ Etagen + 1 (inkl. Untergeschoss)',
    sicherheitsfaktor: 1.0,
    genauigkeit: 'mittel'
}]->(m2);

// kWp → schätzt Modulanzahl: ~2.5 Module pro kWp
MATCH (m1:Merkmal {id: 'MERK_KWP'}), (m2:Merkmal {id: 'MERK_MODULE'})
MERGE (m1)-[:SCHAETZT {
    formel: 'kwp * 2.5',
    beschreibung: '~2.5 Module pro kWp (400Wp Module)',
    sicherheitsfaktor: 1.0,
    genauigkeit: 'mittel'
}]->(m2);

// BGF → schätzt kWp: ~0.015 kWp pro m² Dachfläche (nutzbar)
MATCH (m1:Merkmal {id: 'MERK_BGF'}), (m2:Merkmal {id: 'MERK_KWP'})
MERGE (m1)-[:SCHAETZT {
    formel: '(bgf_m2 / etagen) * 0.6 * 0.015',
    beschreibung: '~60% Dachfläche nutzbar, 15 Wp/m²',
    sicherheitsfaktor: 1.5,
    abhaengig_von: 'MERK_ETAGEN',
    genauigkeit: 'grob'
}]->(m2);

// Melder → schätzt BMA-Zentralen: ~1 Zentrale pro 512 Melder
MATCH (m1:Merkmal {id: 'MERK_MELDER'}), (m2:Merkmal {id: 'MERK_BMA_ZENTRALE'})
MERGE (m1)-[:SCHAETZT {
    formel: 'CEIL(anzahl_melder / 512)',
    beschreibung: 'Max 512 Melder pro Zentrale (Ringbus-Kapazität)',
    sicherheitsfaktor: 1.0,
    genauigkeit: 'mittel'
}]->(m2);


// =============================================================================
// GEBÄUDETYPEN — trigger context-aware rules
// =============================================================================

MERGE (gt_buero:Gebaeudetyp {id: 'GT_BUERO'})
SET gt_buero.name = 'Bürogebäude',
    gt_buero.keywords = 'Büro,Office,Verwaltung,Verwaltungsgebäude';

MERGE (gt_industrie:Gebaeudetyp {id: 'GT_INDUSTRIE'})
SET gt_industrie.name = 'Industriegebäude',
    gt_industrie.keywords = 'Industrie,Fabrik,Produktion,Werk,Halle,Fertigung';

MERGE (gt_handel:Gebaeudetyp {id: 'GT_HANDEL'})
SET gt_handel.name = 'Handelsgebäude',
    gt_handel.keywords = 'Handel,Einkaufszentrum,Mall,Supermarkt,Filiale,Retail';

MERGE (gt_krankenhaus:Gebaeudetyp {id: 'GT_KRANKENHAUS'})
SET gt_krankenhaus.name = 'Krankenhaus / Klinik',
    gt_krankenhaus.keywords = 'Krankenhaus,Klinik,Hospital,Pflege,Altenheim';

MERGE (gt_hotel:Gebaeudetyp {id: 'GT_HOTEL'})
SET gt_hotel.name = 'Hotel / Beherbergung',
    gt_hotel.keywords = 'Hotel,Pension,Hostel,Beherbergung';

MERGE (gt_schule:Gebaeudetyp {id: 'GT_SCHULE'})
SET gt_schule.name = 'Schule / Bildung',
    gt_schule.keywords = 'Schule,Universität,Kindergarten,Kita,Bildung';

MERGE (gt_tiefgarage:Gebaeudetyp {id: 'GT_TIEFGARAGE'})
SET gt_tiefgarage.name = 'Tiefgarage / Parkhaus',
    gt_tiefgarage.keywords = 'Tiefgarage,Parkhaus,Parkdeck,Garage';

MERGE (gt_wohnbau:Gebaeudetyp {id: 'GT_WOHNBAU'})
SET gt_wohnbau.name = 'Wohngebäude / Mehrfamilienhaus',
    gt_wohnbau.keywords = 'Wohnung,Mehrfamilienhaus,WEG,Wohnanlage';

MERGE (gt_versamm:Gebaeudetyp {id: 'GT_VERSAMM'})
SET gt_versamm.name = 'Versammlungsstätte',
    gt_versamm.keywords = 'Veranstaltung,Messe,Stadion,Theater,Kino,Arena,Kongresszentrum';

MERGE (gt_hochhaus:Gebaeudetyp {id: 'GT_HOCHHAUS'})
SET gt_hochhaus.name = 'Hochhaus (>22m Höhe)',
    gt_hochhaus.keywords = 'Hochhaus,Tower,Turm';

MERGE (gt_lager:Gebaeudetyp {id: 'GT_LAGER'})
SET gt_lager.name = 'Lager / Logistik',
    gt_lager.keywords = 'Lager,Logistik,Logistikzentrum,Warehouse';


// =============================================================================
// GEFAHRENZONEN — triggered by Gebäudetyp combinations
// =============================================================================

MERGE (gz_atex:Gefahrenzone {id: 'GZ_ATEX'})
SET gz_atex.name = 'Explosionsgefährdeter Bereich (ATEX)',
    gz_atex.beschreibung = 'Zone 1/2 nach ATEX — Gasgemische durch Batterieladung möglich';

MERGE (gz_nassbereich:Gefahrenzone {id: 'GZ_NASS'})
SET gz_nassbereich.name = 'Nassbereich / erhöhte Feuchte',
    gz_nassbereich.beschreibung = 'Erhöhte Anforderungen an Schutzart (IP55+)';

MERGE (gz_hochvolt:Gefahrenzone {id: 'GZ_HOCHVOLT'})
SET gz_hochvolt.name = 'Hochvolt-Bereich (>1kV AC)',
    gz_hochvolt.beschreibung = 'Erweiterte Schutzmaßnahmen und Qualifikation erforderlich';

MERGE (gz_medizin:Gefahrenzone {id: 'GZ_MEDIZIN'})
SET gz_medizin.name = 'Medizinisch genutzter Bereich',
    gz_medizin.beschreibung = 'Gruppe 1/2 nach DIN VDE 0100-710';

// Gebäudetyp → löst Gefahrenzone aus (context-aware!)
// Tiefgarage + Ladepunkte → ATEX-Prüfung
MATCH (gt:Gebaeudetyp {id: 'GT_TIEFGARAGE'}), (gz:Gefahrenzone {id: 'GZ_ATEX'})
MERGE (gt)-[:LOEST_AUS {
    bedingung: 'wallbox_vorhanden',
    beschreibung: 'Wallboxen in Tiefgaragen können ATEX Zone 2 auslösen (Batterieausgasung)',
    schwere: 'pruefpflichtig'
}]->(gz);

// Krankenhaus → Medizinbereich
MATCH (gt:Gebaeudetyp {id: 'GT_KRANKENHAUS'}), (gz:Gefahrenzone {id: 'GZ_MEDIZIN'})
MERGE (gt)-[:LOEST_AUS {
    bedingung: 'immer',
    beschreibung: 'Medizinisch genutzte Bereiche nach VDE 0100-710',
    schwere: 'pflicht'
}]->(gz);

// Hochhaus → erweiterte BMA + Feuerwehraufzug
MATCH (gt:Gebaeudetyp {id: 'GT_HOCHHAUS'}), (gz:Gefahrenzone {id: 'GZ_HOCHVOLT'})
MERGE (gt)-[:LOEST_AUS {
    bedingung: 'hoehe_ueber_22m',
    beschreibung: 'Hochhäuser erfordern redundante Energieversorgung',
    schwere: 'pruefpflichtig'
}]->(gz);

// Gefahrenzone → erfordert zusätzliche Qualifikation
MATCH (gz:Gefahrenzone {id: 'GZ_ATEX'}), (q:Qualifikation {id: 'QUAL_ATEX'})
MERGE (gz)-[:ERFORDERT_QUALIFIKATION]->(q);

MATCH (gz:Gefahrenzone {id: 'GZ_MEDIZIN'}), (q:Qualifikation {id: 'QUAL_PSV'})
MERGE (gz)-[:ERFORDERT_QUALIFIKATION]->(q);

// Gefahrenzone → Zuschlag auf Preis
MERGE (z_atex:Zuschlag {id: 'ZUSCHLAG_ATEX'})
SET z_atex.name = 'ATEX-Zuschlag',
    z_atex.typ = 'prozent',
    z_atex.wert = 35.0,
    z_atex.beschreibung = 'Mehraufwand für Ex-Schutz-Prüfung';

MERGE (z_medizin:Zuschlag {id: 'ZUSCHLAG_MEDIZIN'})
SET z_medizin.name = 'Medizinbereich-Zuschlag',
    z_medizin.typ = 'prozent',
    z_medizin.wert = 25.0,
    z_medizin.beschreibung = 'Erweiterte Prüfung nach VDE 0100-710';

MATCH (gz:Gefahrenzone {id: 'GZ_ATEX'}), (z:Zuschlag {id: 'ZUSCHLAG_ATEX'})
MERGE (gz)-[:BEWIRKT_ZUSCHLAG]->(z);

MATCH (gz:Gefahrenzone {id: 'GZ_MEDIZIN'}), (z:Zuschlag {id: 'ZUSCHLAG_MEDIZIN'})
MERGE (gz)-[:BEWIRKT_ZUSCHLAG]->(z);


// =============================================================================
// KOSTENTREIBER — the "WHY" layer (causal reasoning)
// =============================================================================
// Analogous to Stressors/Traits in the HVAC graph project.
// Stressors answer: "WHY does this cost more/less?"
// They create causal chains that the agent can traverse to EXPLAIN prices.
//
// Pattern:
//   Context (Gebäudetyp, Merkmal, Situation)
//     →[:EXPOSES_TO]→ Stressor
//       →[:BEWIRKT]→ Effect (Zuschlag, Intervall, Qualifikation, Preisanpassung)
//
// This is NOT just metadata — it's navigable graph structure that enables
// the agent to answer "Warum kostet das 35% mehr?" with a graph traversal.

CREATE CONSTRAINT IF NOT EXISTS FOR (s:Stressor) REQUIRE s.id IS UNIQUE;
CREATE CONSTRAINT IF NOT EXISTS FOR (t:Trait) REQUIRE t.id IS UNIQUE;

// ---------------------------------------------------------------------------
// Stressor Nodes (domain_label: "Kostentreiber" for TÜV SÜD UI)
// ---------------------------------------------------------------------------
// Engine-compatible labels from graph project. display_name in German.

MERGE (kt_sonderbau:Stressor {id: 'KT_SONDERBAU'})
SET kt_sonderbau.name = 'Special Construction (LBO)',
    kt_sonderbau.display_name = 'Sonderbau nach Landesbauordnung',
    kt_sonderbau.domain_label = 'Kostentreiber',
    kt_sonderbau.category = 'regulatory',
    kt_sonderbau.severity = 'HIGH',
    kt_sonderbau.beschreibung = 'Gebäude mit besonderer Art oder Nutzung — erhöhte Prüfanforderungen nach LBO',
    kt_sonderbau.erklaerung = 'Sonderbauten unterliegen verschärften Brandschutz- und Sicherheitsvorschriften. Dies erfordert häufigere Prüfungen durch höher qualifiziertes Personal.';

MERGE (kt_exschutz:Stressor {id: 'KT_EXPLOSIONSSCHUTZ'})
SET kt_exschutz.name = 'Explosion Hazard (ATEX)',
    kt_exschutz.display_name = 'Explosionsgefährdung (ATEX)',
    kt_exschutz.domain_label = 'Kostentreiber',
    kt_exschutz.category = 'safety',
    kt_exschutz.severity = 'CRITICAL',
    kt_exschutz.beschreibung = 'Bereiche mit explosionsfähiger Atmosphäre — Gasgemische, Stäube, Batterieausgasung',
    kt_exschutz.erklaerung = 'In ATEX-Zonen müssen alle elektrischen Betriebsmittel auf Zündschutzart geprüft werden. Dies erfordert speziell qualifizierte Sachverständige und zusätzliche Messverfahren.';

MERGE (kt_altanlage:Stressor {id: 'KT_ALTANLAGE'})
SET kt_altanlage.name = 'Legacy Installation (>25 years)',
    kt_altanlage.display_name = 'Altanlage (>25 Jahre)',
    kt_altanlage.domain_label = 'Kostentreiber',
    kt_altanlage.category = 'technical',
    kt_altanlage.severity = 'MEDIUM',
    kt_altanlage.beschreibung = 'Elektrische Anlage älter als 25 Jahre — erhöhter Prüfaufwand durch fehlende Dokumentation und veraltete Bauteile',
    kt_altanlage.erklaerung = 'Ältere Anlagen haben oft unvollständige Bestandspläne, veraltete Schutzmaßnahmen und Materialermüdung. Die Prüfung dauert länger und erfordert erweiterte Messtechnik.';

MERGE (kt_hoehe:Stressor {id: 'KT_HOEHE'})
SET kt_hoehe.name = 'High-Rise Building (>22m)',
    kt_hoehe.display_name = 'Gebäudehöhe >22m (Hochhaus)',
    kt_hoehe.domain_label = 'Kostentreiber',
    kt_hoehe.category = 'regulatory',
    kt_hoehe.severity = 'HIGH',
    kt_hoehe.beschreibung = 'Hochhäuser erfordern redundante Sicherheitssysteme und spezielle Prüfungen',
    kt_hoehe.erklaerung = 'Ab 22m Höhe gelten die Hochhausrichtlinien: Feuerwehraufzug, Druckbelüftung, redundante Stromversorgung, erweiterte BMA mit Feuerwehr-Bedienfeld.';

MERGE (kt_medizin:Stressor {id: 'KT_MEDIZIN'})
SET kt_medizin.name = 'Medical Area',
    kt_medizin.display_name = 'Medizinisch genutzter Bereich',
    kt_medizin.domain_label = 'Kostentreiber',
    kt_medizin.category = 'safety',
    kt_medizin.severity = 'HIGH',
    kt_medizin.beschreibung = 'Räume der Gruppe 1 und 2 nach VDE 0100-710 — Patientenschutz',
    kt_medizin.erklaerung = 'In medizinischen Bereichen können Fehlerströme lebensbedrohlich sein. Die Prüfung umfasst zusätzlich IT-Systeme, Potentialausgleich und Isolationsüberwachung.';

MERGE (kt_stueckzahl:Stressor {id: 'KT_HOHE_STUECKZAHL'})
SET kt_stueckzahl.name = 'High Volume',
    kt_stueckzahl.display_name = 'Hohe Stückzahl / Volumen',
    kt_stueckzahl.domain_label = 'Kostentreiber',
    kt_stueckzahl.category = 'economic',
    kt_stueckzahl.severity = 'LOW',
    kt_stueckzahl.direction = 'REDUCES_COST',
    kt_stueckzahl.beschreibung = 'Große Mengen gleicher Prüfobjekte — Skaleneffekte bei Rüstzeit und Logistik',
    kt_stueckzahl.erklaerung = 'Bei hohen Stückzahlen sinkt der Aufwand pro Einheit durch eingesparte Rüstzeiten, optimierte Prüfrouten und standardisierte Prüfabläufe.';

MERGE (kt_mehrstandort:Stressor {id: 'KT_MEHRSTANDORT'})
SET kt_mehrstandort.name = 'Multi-Site Contract',
    kt_mehrstandort.display_name = 'Mehrstandort-Vertrag (Filialnetz)',
    kt_mehrstandort.domain_label = 'Kostentreiber',
    kt_mehrstandort.category = 'economic',
    kt_mehrstandort.severity = 'LOW',
    kt_mehrstandort.direction = 'REDUCES_COST',
    kt_mehrstandort.beschreibung = 'Rahmenvertrag über mehrere Standorte — Planungssicherheit ermöglicht Rabatte',
    kt_mehrstandort.erklaerung = 'Mehrstandort-Verträge ermöglichen regionale Tourenplanung, reduzieren Anfahrtskosten pro Standort und sichern wiederkehrendes Geschäft.';

MERGE (kt_erstpruefung:Stressor {id: 'KT_ERSTPRUEFUNG'})
SET kt_erstpruefung.name = 'Initial Inspection',
    kt_erstpruefung.display_name = 'Erstprüfung (keine Vorgeschichte)',
    kt_erstpruefung.domain_label = 'Kostentreiber',
    kt_erstpruefung.category = 'technical',
    kt_erstpruefung.severity = 'MEDIUM',
    kt_erstpruefung.beschreibung = 'Erste Prüfung einer Anlage — kein Vergleich mit Vorjahr möglich',
    kt_erstpruefung.erklaerung = 'Bei Erstprüfungen fehlt die Prüfhistorie. Alle Merkmale müssen vollständig erfasst, Bestandspläne gesichtet und Referenzwerte erstellt werden.';

MERGE (kt_zugaenglichkeit:Stressor {id: 'KT_ZUGAENGLICHKEIT'})
SET kt_zugaenglichkeit.name = 'Limited Accessibility',
    kt_zugaenglichkeit.display_name = 'Eingeschränkte Zugänglichkeit',
    kt_zugaenglichkeit.domain_label = 'Kostentreiber',
    kt_zugaenglichkeit.category = 'logistical',
    kt_zugaenglichkeit.severity = 'MEDIUM',
    kt_zugaenglichkeit.beschreibung = 'Prüfobjekte in schwer zugänglichen Bereichen — Produktionsbereiche, Reinräume, Höhenarbeitsplätze',
    kt_zugaenglichkeit.erklaerung = 'Eingeschränkter Zugang erfordert Begleitpersonal, Sicherheitseinweisungen, spezielle PSA oder Hubarbeitsbühnen. Die Prüfzeit pro Einheit steigt.';

MERGE (kt_zeitdruck:Stressor {id: 'KT_ZEITDRUCK'})
SET kt_zeitdruck.name = 'Time Pressure / Express',
    kt_zeitdruck.display_name = 'Zeitdruck / Express',
    kt_zeitdruck.domain_label = 'Kostentreiber',
    kt_zeitdruck.category = 'logistical',
    kt_zeitdruck.severity = 'MEDIUM',
    kt_zeitdruck.beschreibung = 'Prüfung muss innerhalb kurzer Frist erfolgen — Umdisponierung von Personal nötig',
    kt_zeitdruck.erklaerung = 'Expressprüfungen erfordern kurzfristige Umplanung bestehender Touren und ggf. Wochenend-/Nachtarbeit.';

MERGE (kt_dc_laden:Stressor {id: 'KT_DC_LADEN'})
SET kt_dc_laden.name = 'DC Fast Charging Infrastructure',
    kt_dc_laden.display_name = 'DC-Schnellladeinfrastruktur',
    kt_dc_laden.domain_label = 'Kostentreiber',
    kt_dc_laden.category = 'technical',
    kt_dc_laden.severity = 'MEDIUM',
    kt_dc_laden.beschreibung = 'DC-Ladestationen (>50 kW) — komplexere Prüfung als AC-Wallboxen',
    kt_dc_laden.erklaerung = 'DC-Schnelllader haben Hochvolt-Gleichstromkreise, aktive Kühlung und komplexere Schutzeinrichtungen. Die Prüfung erfordert spezielle Messtechnik und mehr Zeit.';

MERGE (kt_brandlast:Stressor {id: 'KT_BRANDLAST'})
SET kt_brandlast.name = 'High Fire Load',
    kt_brandlast.display_name = 'Erhöhte Brandlast',
    kt_brandlast.domain_label = 'Kostentreiber',
    kt_brandlast.category = 'safety',
    kt_brandlast.severity = 'HIGH',
    kt_brandlast.beschreibung = 'Gebäude mit hoher Brandlast — Lager, Produktion, Rechenzentren',
    kt_brandlast.erklaerung = 'Hohe Brandlasten erfordern umfassendere Brandschutzkonzepte: größere Sprinkleranlagen, mehrstufige BMA, kürzere Prüfintervalle.';


// ---------------------------------------------------------------------------
// Trait Nodes (domain_label: "Effekt" for TÜV SÜD UI)
// ---------------------------------------------------------------------------
// In HVAC: Trait = physical property a product must have.
// In SmartCal: Trait = effect on pricing/process that a Stressor demands.
// Same engine pattern: Stressor -[:DEMANDS_TRAIT]-> Trait

MERGE (t_kuerzeres_intervall:Trait {id: 'EFF_KUERZERES_INTERVALL'})
SET t_kuerzeres_intervall.name = 'Shorter Inspection Interval',
    t_kuerzeres_intervall.display_name = 'Kürzeres Prüfintervall',
    t_kuerzeres_intervall.domain_label = 'Effekt',
    t_kuerzeres_intervall.trait_type = 'intervall',
    t_kuerzeres_intervall.beschreibung = 'Prüfung muss häufiger durchgeführt werden';

MERGE (t_hoehere_quali:Trait {id: 'EFF_HOEHERE_QUALIFIKATION'})
SET t_hoehere_quali.name = 'Higher Qualification Required',
    t_hoehere_quali.display_name = 'Höhere Qualifikationsanforderung',
    t_hoehere_quali.domain_label = 'Effekt',
    t_hoehere_quali.trait_type = 'qualifikation',
    t_hoehere_quali.beschreibung = 'PSV oder ZÜS statt Befähigte Person — höherer Stundensatz';

MERGE (t_mehr_messungen:Trait {id: 'EFF_MEHR_MESSUNGEN'})
SET t_mehr_messungen.name = 'Extended Measurements',
    t_mehr_messungen.display_name = 'Erweiterte Messungen',
    t_mehr_messungen.domain_label = 'Effekt',
    t_mehr_messungen.trait_type = 'effort',
    t_mehr_messungen.beschreibung = 'Zusätzliche Messpunkte, Isolationsprüfung, Thermografie';

MERGE (t_zuschlag:Trait {id: 'EFF_PREISZUSCHLAG'})
SET t_zuschlag.name = 'Price Surcharge',
    t_zuschlag.display_name = 'Preiszuschlag',
    t_zuschlag.domain_label = 'Effekt',
    t_zuschlag.trait_type = 'price',
    t_zuschlag.beschreibung = 'Prozentualer Aufschlag auf den Grundpreis';

MERGE (t_rabatt:Trait {id: 'EFF_PREISRABATT'})
SET t_rabatt.name = 'Price Discount / Volume Tier',
    t_rabatt.display_name = 'Preisrabatt / Staffel',
    t_rabatt.domain_label = 'Effekt',
    t_rabatt.trait_type = 'price',
    t_rabatt.beschreibung = 'Skaleneffekte senken den Einheitspreis';

MERGE (t_pflicht:Trait {id: 'EFF_ZUSAETZLICHE_PRUEFPFLICHT'})
SET t_pflicht.name = 'Additional Mandatory Inspection',
    t_pflicht.display_name = 'Zusätzliche Prüfpflicht',
    t_pflicht.domain_label = 'Effekt',
    t_pflicht.trait_type = 'obligation',
    t_pflicht.beschreibung = 'Weitere Dienstleistung wird regulatorisch erforderlich';

MERGE (t_doku:Trait {id: 'EFF_ERWEITERTE_DOKU'})
SET t_doku.name = 'Extended Documentation',
    t_doku.display_name = 'Erweiterte Dokumentation',
    t_doku.domain_label = 'Effekt',
    t_doku.trait_type = 'effort',
    t_doku.beschreibung = 'Fotodokumentation, Mängelkatalog, Prüfbericht mit Detailfotos';

MERGE (t_spezialgeraet:Trait {id: 'EFF_SPEZIALGERAET'})
SET t_spezialgeraet.name = 'Specialized Equipment Required',
    t_spezialgeraet.display_name = 'Spezielle Messtechnik erforderlich',
    t_spezialgeraet.domain_label = 'Effekt',
    t_spezialgeraet.trait_type = 'effort',
    t_spezialgeraet.beschreibung = 'Wärmebildkamera, DC-Messtechnik, Isolationsüberwachung';

MERGE (t_buendel:Trait {id: 'EFF_BUENDELRABATT'})
SET t_buendel.name = 'Bundle Discount Possible',
    t_buendel.display_name = 'Bündelrabatt möglich',
    t_buendel.domain_label = 'Effekt',
    t_buendel.trait_type = 'price',
    t_buendel.beschreibung = 'Mehrere Leistungen am gleichen Tag = geteilte Anfahrt und Rüstzeit';


// ---------------------------------------------------------------------------
// EXPOSES_TO: Context → Stressor (what triggers the cost driver?)
// ---------------------------------------------------------------------------

// Gebäudetyp exposes to Stressor
MATCH (gt:Gebaeudetyp {id: 'GT_KRANKENHAUS'}), (kt:Stressor {id: 'KT_SONDERBAU'})
MERGE (gt)-[:EXPOSES_TO {immer: true}]->(kt);
MATCH (gt:Gebaeudetyp {id: 'GT_HOTEL'}), (kt:Stressor {id: 'KT_SONDERBAU'})
MERGE (gt)-[:EXPOSES_TO {immer: true}]->(kt);
MATCH (gt:Gebaeudetyp {id: 'GT_VERSAMM'}), (kt:Stressor {id: 'KT_SONDERBAU'})
MERGE (gt)-[:EXPOSES_TO {immer: true}]->(kt);
MATCH (gt:Gebaeudetyp {id: 'GT_HOCHHAUS'}), (kt:Stressor {id: 'KT_SONDERBAU'})
MERGE (gt)-[:EXPOSES_TO {immer: true}]->(kt);
MATCH (gt:Gebaeudetyp {id: 'GT_HANDEL'}), (kt:Stressor {id: 'KT_SONDERBAU'})
MERGE (gt)-[:EXPOSES_TO {bedingung: 'bgf_m2 > 2000'}]->(kt);

MATCH (gt:Gebaeudetyp {id: 'GT_HOCHHAUS'}), (kt:Stressor {id: 'KT_HOEHE'})
MERGE (gt)-[:EXPOSES_TO {immer: true}]->(kt);

MATCH (gt:Gebaeudetyp {id: 'GT_KRANKENHAUS'}), (kt:Stressor {id: 'KT_MEDIZIN'})
MERGE (gt)-[:EXPOSES_TO {immer: true}]->(kt);

MATCH (gt:Gebaeudetyp {id: 'GT_LAGER'}), (kt:Stressor {id: 'KT_BRANDLAST'})
MERGE (gt)-[:EXPOSES_TO {immer: true}]->(kt);
MATCH (gt:Gebaeudetyp {id: 'GT_INDUSTRIE'}), (kt:Stressor {id: 'KT_BRANDLAST'})
MERGE (gt)-[:EXPOSES_TO {bedingung: 'brandlast = hoch'}]->(kt);

// Gefahrenzone exposes to Stressor
MATCH (gz:Gefahrenzone {id: 'GZ_ATEX'}), (kt:Stressor {id: 'KT_EXPLOSIONSSCHUTZ'})
MERGE (gz)-[:EXPOSES_TO {immer: true}]->(kt);
MATCH (gz:Gefahrenzone {id: 'GZ_MEDIZIN'}), (kt:Stressor {id: 'KT_MEDIZIN'})
MERGE (gz)-[:EXPOSES_TO {immer: true}]->(kt);

// Merkmal exposes to Stressor (conditional)
MATCH (m:Merkmal {id: 'MERK_ANLAGENALTER'}), (kt:Stressor {id: 'KT_ALTANLAGE'})
MERGE (m)-[:EXPOSES_TO {bedingung: 'anlagenalter_jahre > 25'}]->(kt);

MATCH (m:Merkmal {id: 'MERK_LADETYP'}), (kt:Stressor {id: 'KT_DC_LADEN'})
MERGE (m)-[:EXPOSES_TO {bedingung: 'ladetyp = DC'}]->(kt);

MATCH (m:Merkmal {id: 'MERK_STANDORTE'}), (kt:Stressor {id: 'KT_MEHRSTANDORT'})
MERGE (m)-[:EXPOSES_TO {bedingung: 'anzahl_standorte >= 3'}]->(kt);


// ---------------------------------------------------------------------------
// DEMANDS_TRAIT: Stressor → Trait (what does the cost driver cause?)
// ---------------------------------------------------------------------------

// Sonderbau → multiple effects
MATCH (kt:Stressor {id: 'KT_SONDERBAU'}), (eff:Trait {id: 'EFF_KUERZERES_INTERVALL'})
MERGE (kt)-[:DEMANDS_TRAIT {staerke: 'hoch', erklaerung: 'Sonderbauten: Prüfintervall halbiert sich (z.B. 4J→2J)'}]->(eff);
MATCH (kt:Stressor {id: 'KT_SONDERBAU'}), (eff:Trait {id: 'EFF_HOEHERE_QUALIFIKATION'})
MERGE (kt)-[:DEMANDS_TRAIT {staerke: 'hoch', erklaerung: 'PSV statt Befähigte Person erforderlich'}]->(eff);
MATCH (kt:Stressor {id: 'KT_SONDERBAU'}), (eff:Trait {id: 'EFF_ZUSAETZLICHE_PRUEFPFLICHT'})
MERGE (kt)-[:DEMANDS_TRAIT {staerke: 'hoch', erklaerung: 'BMA, Sprinkler, Blitzschutz werden Pflicht'}]->(eff);

// Explosionsschutz → effects
MATCH (kt:Stressor {id: 'KT_EXPLOSIONSSCHUTZ'}), (eff:Trait {id: 'EFF_PREISZUSCHLAG'})
MERGE (kt)-[:DEMANDS_TRAIT {staerke: 'hoch', wert: 35.0, einheit: 'prozent', erklaerung: 'Ex-Schutz-Prüfung erfordert spezielle Messtechnik und ATEX-Sachkundigen'}]->(eff);
MATCH (kt:Stressor {id: 'KT_EXPLOSIONSSCHUTZ'}), (eff:Trait {id: 'EFF_HOEHERE_QUALIFIKATION'})
MERGE (kt)-[:DEMANDS_TRAIT {staerke: 'hoch', erklaerung: 'Explosionsschutz-Sachkundiger nach TRBS 1203-2 erforderlich'}]->(eff);
MATCH (kt:Stressor {id: 'KT_EXPLOSIONSSCHUTZ'}), (eff:Trait {id: 'EFF_SPEZIALGERAET'})
MERGE (kt)-[:DEMANDS_TRAIT {staerke: 'mittel', erklaerung: 'Ex-geschützte Messgeräte und Dokumentation der Zündschutzarten'}]->(eff);

// Altanlage → effects
MATCH (kt:Stressor {id: 'KT_ALTANLAGE'}), (eff:Trait {id: 'EFF_PREISZUSCHLAG'})
MERGE (kt)-[:DEMANDS_TRAIT {staerke: 'mittel', wert: 20.0, einheit: 'prozent', erklaerung: 'Fehlende Bestandspläne, veraltete Bauteile, erhöhter Messaufwand'}]->(eff);
MATCH (kt:Stressor {id: 'KT_ALTANLAGE'}), (eff:Trait {id: 'EFF_ERWEITERTE_DOKU'})
MERGE (kt)-[:DEMANDS_TRAIT {staerke: 'mittel', erklaerung: 'Detaillierte Mängeldokumentation mit Fotos und Handlungsempfehlungen'}]->(eff);
MATCH (kt:Stressor {id: 'KT_ALTANLAGE'}), (eff:Trait {id: 'EFF_KUERZERES_INTERVALL'})
MERGE (kt)-[:DEMANDS_TRAIT {staerke: 'mittel', erklaerung: 'Bei schwerwiegenden Mängeln: verkürztes Prüfintervall empfohlen'}]->(eff);

// Hochhaus → effects
MATCH (kt:Stressor {id: 'KT_HOEHE'}), (eff:Trait {id: 'EFF_ZUSAETZLICHE_PRUEFPFLICHT'})
MERGE (kt)-[:DEMANDS_TRAIT {staerke: 'hoch', erklaerung: 'Feuerwehraufzug, Druckbelüftung, redundante Stromversorgung — alles prüfpflichtig'}]->(eff);
MATCH (kt:Stressor {id: 'KT_HOEHE'}), (eff:Trait {id: 'EFF_MEHR_MESSUNGEN'})
MERGE (kt)-[:DEMANDS_TRAIT {staerke: 'mittel', erklaerung: 'Funktionsprüfung Feuerwehr-Bedienfeld, Druckdifferenzmessung Schleuse'}]->(eff);

// Medizin → effects
MATCH (kt:Stressor {id: 'KT_MEDIZIN'}), (eff:Trait {id: 'EFF_PREISZUSCHLAG'})
MERGE (kt)-[:DEMANDS_TRAIT {staerke: 'hoch', wert: 25.0, einheit: 'prozent', erklaerung: 'Prüfung IT-System, Potentialausgleich, Isolationsüberwachung nach VDE 0100-710'}]->(eff);
MATCH (kt:Stressor {id: 'KT_MEDIZIN'}), (eff:Trait {id: 'EFF_HOEHERE_QUALIFIKATION'})
MERGE (kt)-[:DEMANDS_TRAIT {staerke: 'hoch', erklaerung: 'Prüfsachverständiger mit Erfahrung in medizinischen Bereichen'}]->(eff);
MATCH (kt:Stressor {id: 'KT_MEDIZIN'}), (eff:Trait {id: 'EFF_SPEZIALGERAET'})
MERGE (kt)-[:DEMANDS_TRAIT {staerke: 'mittel', erklaerung: 'Isolationsüberwachung, Ableitstrommessung medizinischer Geräte'}]->(eff);

// Hohe Stückzahl → Rabatt (cost REDUCER)
MATCH (kt:Stressor {id: 'KT_HOHE_STUECKZAHL'}), (eff:Trait {id: 'EFF_PREISRABATT'})
MERGE (kt)-[:DEMANDS_TRAIT {staerke: 'hoch', erklaerung: 'Staffelpreise: ab 500 Stk -15%, ab 1000 Stk -29%, ab 2500 Stk -38%'}]->(eff);
MATCH (kt:Stressor {id: 'KT_HOHE_STUECKZAHL'}), (eff:Trait {id: 'EFF_BUENDELRABATT'})
MERGE (kt)-[:DEMANDS_TRAIT {staerke: 'mittel', erklaerung: 'Mehrere Leistungen am gleichen Tag möglich → geteilte Anfahrt'}]->(eff);

// Mehrstandort → Rabatt
MATCH (kt:Stressor {id: 'KT_MEHRSTANDORT'}), (eff:Trait {id: 'EFF_PREISRABATT'})
MERGE (kt)-[:DEMANDS_TRAIT {staerke: 'hoch', erklaerung: 'Rahmenvertrag mit Planungssicherheit: Tourenoptimierung, reduzierte Anfahrtkosten'}]->(eff);

// Erstprüfung → Zuschlag
MATCH (kt:Stressor {id: 'KT_ERSTPRUEFUNG'}), (eff:Trait {id: 'EFF_PREISZUSCHLAG'})
MERGE (kt)-[:DEMANDS_TRAIT {staerke: 'mittel', wert: 30.0, einheit: 'prozent', erklaerung: 'Vollständige Bestandsaufnahme statt Delta-Prüfung'}]->(eff);
MATCH (kt:Stressor {id: 'KT_ERSTPRUEFUNG'}), (eff:Trait {id: 'EFF_ERWEITERTE_DOKU'})
MERGE (kt)-[:DEMANDS_TRAIT {staerke: 'hoch', erklaerung: 'Erstmalige Erstellung des Prüfberichts mit vollständiger Anlagenerfassung'}]->(eff);

// Zeitdruck → Zuschlag
MATCH (kt:Stressor {id: 'KT_ZEITDRUCK'}), (eff:Trait {id: 'EFF_PREISZUSCHLAG'})
MERGE (kt)-[:DEMANDS_TRAIT {staerke: 'hoch', wert: 25.0, einheit: 'prozent', erklaerung: 'Kurzfristige Umdisponierung, ggf. Wochenendarbeit'}]->(eff);

// DC-Laden → Zuschlag + Spezialgerät
MATCH (kt:Stressor {id: 'KT_DC_LADEN'}), (eff:Trait {id: 'EFF_PREISZUSCHLAG'})
MERGE (kt)-[:DEMANDS_TRAIT {staerke: 'mittel', wert: 65.5, einheit: 'prozent_auf_wallbox', erklaerung: 'DC-Prüfung: +95€/LP auf 145€ Basispreis = ~65% Zuschlag'}]->(eff);
MATCH (kt:Stressor {id: 'KT_DC_LADEN'}), (eff:Trait {id: 'EFF_SPEZIALGERAET'})
MERGE (kt)-[:DEMANDS_TRAIT {staerke: 'hoch', erklaerung: 'DC-Isolationsmessung, Hochvolt-Schutzprüfung, Kühlkreislauf-Kontrolle'}]->(eff);

// Zugänglichkeit → Zuschlag
MATCH (kt:Stressor {id: 'KT_ZUGAENGLICHKEIT'}), (eff:Trait {id: 'EFF_PREISZUSCHLAG'})
MERGE (kt)-[:DEMANDS_TRAIT {staerke: 'mittel', wert: 15.0, einheit: 'prozent', erklaerung: 'Begleitpersonal, Sicherheitseinweisung, PSA, verlängerte Prüfzeit'}]->(eff);

// Brandlast → effects
MATCH (kt:Stressor {id: 'KT_BRANDLAST'}), (eff:Trait {id: 'EFF_ZUSAETZLICHE_PRUEFPFLICHT'})
MERGE (kt)-[:DEMANDS_TRAIT {staerke: 'hoch', erklaerung: 'Sprinkleranlage wird bei hoher Brandlast pflicht (IndBauRL)'}]->(eff);
MATCH (kt:Stressor {id: 'KT_BRANDLAST'}), (eff:Trait {id: 'EFF_KUERZERES_INTERVALL'})
MERGE (kt)-[:DEMANDS_TRAIT {staerke: 'mittel', erklaerung: 'BMA-Prüfintervall verkürzt sich bei erhöhter Brandlast'}]->(eff);


// ---------------------------------------------------------------------------
// STRESSOR → DIENSTLEISTUNG via AFFECTS (which services are affected?)
// ---------------------------------------------------------------------------
// This creates cross-links: same Stressor affects multiple services.

// Sonderbau betrifft BMA, Sprinkler, Blitzschutz, Aufzug
MATCH (kt:Stressor {id: 'KT_SONDERBAU'}), (dl:Dienstleistung {id: 'DL_BMA'})
MERGE (kt)-[:AFFECTS {erklaerung: 'BMA wird Pflichtprüfung in Sonderbauten'}]->(dl);
MATCH (kt:Stressor {id: 'KT_SONDERBAU'}), (dl:Dienstleistung {id: 'DL_SPRINKLER'})
MERGE (kt)-[:AFFECTS {erklaerung: 'Sprinkleranlage oft Pflicht in Sonderbauten'}]->(dl);
MATCH (kt:Stressor {id: 'KT_SONDERBAU'}), (dl:Dienstleistung {id: 'DL_BLITZ'})
MERGE (kt)-[:AFFECTS {erklaerung: 'Blitzschutzklasse I/II für Sonderbauten'}]->(dl);
MATCH (kt:Stressor {id: 'KT_SONDERBAU'}), (dl:Dienstleistung {id: 'DL_AUFZUG_HP'})
MERGE (kt)-[:AFFECTS {erklaerung: 'Feuerwehraufzug in Sonderbauten mit >13m Höhe'}]->(dl);

// ATEX betrifft Wallbox, DGUV ortsfest
MATCH (kt:Stressor {id: 'KT_EXPLOSIONSSCHUTZ'}), (dl:Dienstleistung {id: 'DL_WALLBOX'})
MERGE (kt)-[:AFFECTS {erklaerung: 'Wallboxen in Ex-Zone: Zündschutzart-Prüfung'}]->(dl);
MATCH (kt:Stressor {id: 'KT_EXPLOSIONSSCHUTZ'}), (dl:Dienstleistung {id: 'DL_DGUV_ORTF'})
MERGE (kt)-[:AFFECTS {erklaerung: 'Ortsfeste Anlagen in Ex-Zone: erweiterte DGUV V3'}]->(dl);

// Altanlage betrifft DGUV ortsfest, Thermografie
MATCH (kt:Stressor {id: 'KT_ALTANLAGE'}), (dl:Dienstleistung {id: 'DL_DGUV_ORTF'})
MERGE (kt)-[:AFFECTS {erklaerung: 'Erhöhter Prüfaufwand bei Altanlagen >25 Jahre'}]->(dl);
MATCH (kt:Stressor {id: 'KT_ALTANLAGE'}), (dl:Dienstleistung {id: 'DL_THERMO'})
MERGE (kt)-[:AFFECTS {erklaerung: 'Thermografie bei Altanlagen besonders empfohlen (Hot-Spot-Risiko)'}]->(dl);

// Medizin betrifft DGUV, BMA
MATCH (kt:Stressor {id: 'KT_MEDIZIN'}), (dl:Dienstleistung {id: 'DL_DGUV_ORTF'})
MERGE (kt)-[:AFFECTS {erklaerung: 'Elektrische Anlagen in med. Bereichen: VDE 0100-710'}]->(dl);
MATCH (kt:Stressor {id: 'KT_MEDIZIN'}), (dl:Dienstleistung {id: 'DL_BMA'})
MERGE (kt)-[:AFFECTS {erklaerung: 'BMA in Krankenhäusern: erweiterte Anforderungen DIN 14675'}]->(dl);

// DC-Laden betrifft Wallbox
MATCH (kt:Stressor {id: 'KT_DC_LADEN'}), (dl:Dienstleistung {id: 'DL_WALLBOX'})
MERGE (kt)-[:AFFECTS {erklaerung: 'DC-Schnelllader: erweiterter Prüfumfang + Spezialmesstechnik'}]->(dl);

// Brandlast betrifft BMA, Sprinkler
MATCH (kt:Stressor {id: 'KT_BRANDLAST'}), (dl:Dienstleistung {id: 'DL_BMA'})
MERGE (kt)-[:AFFECTS {erklaerung: 'Erhöhte Brandlast → kürzeres BMA-Prüfintervall'}]->(dl);
MATCH (kt:Stressor {id: 'KT_BRANDLAST'}), (dl:Dienstleistung {id: 'DL_SPRINKLER'})
MERGE (kt)-[:AFFECTS {erklaerung: 'Sprinkleranlage bei hoher Brandlast pflicht nach IndBauRL'}]->(dl);


// =============================================================================
// NUTZUNGSARTEN & PRÜFINTERVALLE — regulatory graph
// =============================================================================

MERGE (na_buero:Nutzungsart {id: 'NUTZ_BUERO'})
SET na_buero.name = 'Büro/Verwaltung';

MERGE (na_industrie:Nutzungsart {id: 'NUTZ_INDUSTRIE'})
SET na_industrie.name = 'Industrie/Produktion';

MERGE (na_oeffentlich:Nutzungsart {id: 'NUTZ_OEFFENTLICH'})
SET na_oeffentlich.name = 'Öffentlich zugänglich';

MERGE (na_wohnen:Nutzungsart {id: 'NUTZ_WOHNEN'})
SET na_wohnen.name = 'Wohnen';

// Nutzungsart bestimmt Prüfintervall (same Norm, different interval!)
MERGE (pi_1j:Pruefintervall {id: 'PI_1J'})
SET pi_1j.monate = 12, pi_1j.label = 'jährlich';

MERGE (pi_2j:Pruefintervall {id: 'PI_2J'})
SET pi_2j.monate = 24, pi_2j.label = 'alle 2 Jahre';

MERGE (pi_3j:Pruefintervall {id: 'PI_3J'})
SET pi_3j.monate = 36, pi_3j.label = 'alle 3 Jahre';

MERGE (pi_4j:Pruefintervall {id: 'PI_4J'})
SET pi_4j.monate = 48, pi_4j.label = 'alle 4 Jahre';

MERGE (pi_6m:Pruefintervall {id: 'PI_6M'})
SET pi_6m.monate = 6, pi_6m.label = 'halbjährlich';

// Gebäudetyp → Nutzungsart
MATCH (gt:Gebaeudetyp {id: 'GT_BUERO'}), (na:Nutzungsart {id: 'NUTZ_BUERO'})
MERGE (gt)-[:HAT_NUTZUNGSART]->(na);

MATCH (gt:Gebaeudetyp {id: 'GT_INDUSTRIE'}), (na:Nutzungsart {id: 'NUTZ_INDUSTRIE'})
MERGE (gt)-[:HAT_NUTZUNGSART]->(na);

MATCH (gt:Gebaeudetyp {id: 'GT_HANDEL'}), (na:Nutzungsart {id: 'NUTZ_OEFFENTLICH'})
MERGE (gt)-[:HAT_NUTZUNGSART]->(na);

MATCH (gt:Gebaeudetyp {id: 'GT_KRANKENHAUS'}), (na:Nutzungsart {id: 'NUTZ_OEFFENTLICH'})
MERGE (gt)-[:HAT_NUTZUNGSART]->(na);

MATCH (gt:Gebaeudetyp {id: 'GT_SCHULE'}), (na:Nutzungsart {id: 'NUTZ_OEFFENTLICH'})
MERGE (gt)-[:HAT_NUTZUNGSART]->(na);

MATCH (gt:Gebaeudetyp {id: 'GT_VERSAMM'}), (na:Nutzungsart {id: 'NUTZ_OEFFENTLICH'})
MERGE (gt)-[:HAT_NUTZUNGSART]->(na);

MATCH (gt:Gebaeudetyp {id: 'GT_WOHNBAU'}), (na:Nutzungsart {id: 'NUTZ_WOHNEN'})
MERGE (gt)-[:HAT_NUTZUNGSART]->(na);


// =============================================================================
// REGIONEN — location-based pricing
// =============================================================================

MERGE (r_sued:Region {id: 'REG_SUED'})
SET r_sued.name = 'Süddeutschland',
    r_sued.bundeslaender = 'Bayern,Baden-Württemberg',
    r_sued.preisfaktor = 1.0;

MERGE (r_west:Region {id: 'REG_WEST'})
SET r_west.name = 'Westdeutschland',
    r_west.bundeslaender = 'NRW,Hessen,Rheinland-Pfalz,Saarland',
    r_west.preisfaktor = 0.95;

MERGE (r_nord:Region {id: 'REG_NORD'})
SET r_nord.name = 'Norddeutschland',
    r_nord.bundeslaender = 'Niedersachsen,Schleswig-Holstein,Hamburg,Bremen',
    r_nord.preisfaktor = 0.92;

MERGE (r_ost:Region {id: 'REG_OST'})
SET r_ost.name = 'Ostdeutschland',
    r_ost.bundeslaender = 'Sachsen,Thüringen,Brandenburg,Berlin,MV,Sachsen-Anhalt',
    r_ost.preisfaktor = 0.88;


// =============================================================================
// ZUSCHLÄGE (Surcharges) — shared across services
// =============================================================================

MERGE (z_express:Zuschlag {id: 'ZUSCHLAG_EXPRESS'})
SET z_express.name = 'Expresszuschlag',
    z_express.typ = 'prozent',
    z_express.wert = 25.0,
    z_express.beschreibung = 'Prüfung innerhalb von 5 Werktagen',
    z_express.bedingung = 'express_gewuenscht';

MERGE (z_wochenende:Zuschlag {id: 'ZUSCHLAG_WOCHENENDE'})
SET z_wochenende.name = 'Wochenend-/Feiertagszuschlag',
    z_wochenende.typ = 'prozent',
    z_wochenende.wert = 50.0,
    z_wochenende.beschreibung = 'Prüfung an Samstagen, Sonntagen oder Feiertagen';

MERGE (z_nacht:Zuschlag {id: 'ZUSCHLAG_NACHT'})
SET z_nacht.name = 'Nachtzuschlag',
    z_nacht.typ = 'prozent',
    z_nacht.wert = 30.0,
    z_nacht.beschreibung = 'Prüfung zwischen 20:00 und 06:00 Uhr';

MERGE (z_doku:Zuschlag {id: 'ZUSCHLAG_DOKU'})
SET z_doku.name = 'Erweiterte Dokumentation',
    z_doku.typ = 'prozent',
    z_doku.wert = 15.0,
    z_doku.beschreibung = 'Inkl. Fotodokumentation und detailliertem Mängelkatalog';

MERGE (z_altanlage:Zuschlag {id: 'ZUSCHLAG_ALTANLAGE'})
SET z_altanlage.name = 'Altanlagen-Zuschlag',
    z_altanlage.typ = 'prozent',
    z_altanlage.wert = 20.0,
    z_altanlage.beschreibung = 'Anlage älter als 25 Jahre — erhöhter Prüfaufwand',
    z_altanlage.bedingung = 'anlagenalter_jahre > 25';

MERGE (z_erstpruefung:Zuschlag {id: 'ZUSCHLAG_ERSTPRUEFUNG'})
SET z_erstpruefung.name = 'Erstprüfungszuschlag',
    z_erstpruefung.typ = 'prozent',
    z_erstpruefung.wert = 30.0,
    z_erstpruefung.beschreibung = 'Erstmalige Prüfung — umfangreicher als Wiederholungsprüfung';


// =============================================================================
// DIENSTLEISTUNGEN (Services) — the core catalog
// =============================================================================

// ---------------------------------------------------------------------------
// EG-001: DGUV V3 — Ortsveränderliche Geräte
// ---------------------------------------------------------------------------
MERGE (dl_dguv_ortv:Dienstleistung {id: 'DL_DGUV_ORTV'})
SET dl_dguv_ortv.code = 'EG-001',
    dl_dguv_ortv.name = 'DGUV V3 — Prüfung ortsveränderlicher Geräte',
    dl_dguv_ortv.kurz = 'Geräteprüfung (ortsveränderlich)',
    dl_dguv_ortv.beschreibung = 'Wiederkehrende Prüfung elektrischer Betriebsmittel nach DGUV Vorschrift 3 und VDE 0701-0702',
    dl_dguv_ortv.kategorie = 'Elektrotechnik',
    dl_dguv_ortv.typischer_aufwand_h = 0.05;

// Preispositionen
MERGE (pp_dguv_ortv:Preisposition {id: 'PP_DGUV_ORTV_GERAET'})
SET pp_dguv_ortv.name = 'Prüfung pro Gerät',
    pp_dguv_ortv.einheit = 'Gerät',
    pp_dguv_ortv.bezugs_merkmal = 'anzahl_geraete',
    pp_dguv_ortv.basispreis = 4.50,
    pp_dguv_ortv.mindestmenge = 50;

MATCH (dl:Dienstleistung {id: 'DL_DGUV_ORTV'}), (pp:Preisposition {id: 'PP_DGUV_ORTV_GERAET'})
MERGE (dl)-[:HAT_PREISPOSITION]->(pp);

// Staffelpreise
MERGE (st1:Staffel {id: 'ST_DGUV_ORTV_500'})
SET st1.ab_menge = 500, st1.preis = 3.80, st1.label = 'ab 500 Geräte';
MERGE (st2:Staffel {id: 'ST_DGUV_ORTV_1000'})
SET st2.ab_menge = 1000, st2.preis = 3.20, st2.label = 'ab 1.000 Geräte';
MERGE (st3:Staffel {id: 'ST_DGUV_ORTV_2500'})
SET st3.ab_menge = 2500, st3.preis = 2.80, st3.label = 'ab 2.500 Geräte';

MATCH (pp:Preisposition {id: 'PP_DGUV_ORTV_GERAET'}), (st:Staffel {id: 'ST_DGUV_ORTV_500'})
MERGE (pp)-[:HAT_STAFFEL]->(st);
MATCH (pp:Preisposition {id: 'PP_DGUV_ORTV_GERAET'}), (st:Staffel {id: 'ST_DGUV_ORTV_1000'})
MERGE (pp)-[:HAT_STAFFEL]->(st);
MATCH (pp:Preisposition {id: 'PP_DGUV_ORTV_GERAET'}), (st:Staffel {id: 'ST_DGUV_ORTV_2500'})
MERGE (pp)-[:HAT_STAFFEL]->(st);

// Norm + Qualifikation links
MATCH (dl:Dienstleistung {id: 'DL_DGUV_ORTV'}), (n:Norm {id: 'NORM_DGUV3'})
MERGE (dl)-[:BASIERT_AUF]->(n);
MATCH (dl:Dienstleistung {id: 'DL_DGUV_ORTV'}), (q:Qualifikation {id: 'QUAL_BEFP'})
MERGE (dl)-[:ERFORDERT_QUALIFIKATION]->(q);

// Merkmal links
MATCH (dl:Dienstleistung {id: 'DL_DGUV_ORTV'}), (m:Merkmal {id: 'MERK_GERAETE'})
MERGE (dl)-[:ERFORDERT_MERKMAL {prioritaet: 1}]->(m);

// Nutzungsart → Prüfintervall für diese DL
MATCH (na:Nutzungsart {id: 'NUTZ_BUERO'}), (pi:Pruefintervall {id: 'PI_2J'}), (dl:Dienstleistung {id: 'DL_DGUV_ORTV'})
MERGE (na)-[:BESTIMMT_INTERVALL {fuer_dl: dl.id}]->(pi);
MATCH (na:Nutzungsart {id: 'NUTZ_INDUSTRIE'}), (pi:Pruefintervall {id: 'PI_1J'}), (dl:Dienstleistung {id: 'DL_DGUV_ORTV'})
MERGE (na)-[:BESTIMMT_INTERVALL {fuer_dl: dl.id}]->(pi);
MATCH (na:Nutzungsart {id: 'NUTZ_OEFFENTLICH'}), (pi:Pruefintervall {id: 'PI_1J'}), (dl:Dienstleistung {id: 'DL_DGUV_ORTV'})
MERGE (na)-[:BESTIMMT_INTERVALL {fuer_dl: dl.id}]->(pi);


// ---------------------------------------------------------------------------
// EG-002: DGUV V3 — Ortsfeste Anlagen
// ---------------------------------------------------------------------------
MERGE (dl_dguv_ortf:Dienstleistung {id: 'DL_DGUV_ORTF'})
SET dl_dguv_ortf.code = 'EG-002',
    dl_dguv_ortf.name = 'DGUV V3 — Prüfung ortsfester Anlagen',
    dl_dguv_ortf.kurz = 'Anlagenprüfung (ortsfest)',
    dl_dguv_ortf.beschreibung = 'Wiederkehrende Prüfung ortsfester elektrischer Anlagen nach DGUV V3 und VDE 0105-100',
    dl_dguv_ortf.kategorie = 'Elektrotechnik';

MERGE (pp_dguv_ortf:Preisposition {id: 'PP_DGUV_ORTF_SK'})
SET pp_dguv_ortf.name = 'Prüfung pro Stromkreis',
    pp_dguv_ortf.einheit = 'Stromkreis',
    pp_dguv_ortf.bezugs_merkmal = 'anzahl_stromkreise',
    pp_dguv_ortf.basispreis = 12.00;

MATCH (dl:Dienstleistung {id: 'DL_DGUV_ORTF'}), (pp:Preisposition {id: 'PP_DGUV_ORTF_SK'})
MERGE (dl)-[:HAT_PREISPOSITION]->(pp);

MERGE (st4:Staffel {id: 'ST_DGUV_ORTF_100'})
SET st4.ab_menge = 100, st4.preis = 10.50;
MERGE (st5:Staffel {id: 'ST_DGUV_ORTF_250'})
SET st5.ab_menge = 250, st5.preis = 9.00;

MATCH (pp:Preisposition {id: 'PP_DGUV_ORTF_SK'}), (st:Staffel {id: 'ST_DGUV_ORTF_100'})
MERGE (pp)-[:HAT_STAFFEL]->(st);
MATCH (pp:Preisposition {id: 'PP_DGUV_ORTF_SK'}), (st:Staffel {id: 'ST_DGUV_ORTF_250'})
MERGE (pp)-[:HAT_STAFFEL]->(st);

MATCH (dl:Dienstleistung {id: 'DL_DGUV_ORTF'}), (n:Norm {id: 'NORM_DGUV3'})
MERGE (dl)-[:BASIERT_AUF]->(n);
MATCH (dl:Dienstleistung {id: 'DL_DGUV_ORTF'}), (n:Norm {id: 'NORM_VDE0105'})
MERGE (dl)-[:BASIERT_AUF]->(n);
MATCH (dl:Dienstleistung {id: 'DL_DGUV_ORTF'}), (q:Qualifikation {id: 'QUAL_EFK'})
MERGE (dl)-[:ERFORDERT_QUALIFIKATION]->(q);

MATCH (dl:Dienstleistung {id: 'DL_DGUV_ORTF'}), (m:Merkmal {id: 'MERK_STROMKREISE'})
MERGE (dl)-[:ERFORDERT_MERKMAL {prioritaet: 1}]->(m);
MATCH (dl:Dienstleistung {id: 'DL_DGUV_ORTF'}), (m:Merkmal {id: 'MERK_SCHALTANLAGEN'})
MERGE (dl)-[:ERFORDERT_MERKMAL {prioritaet: 2}]->(m);
MATCH (dl:Dienstleistung {id: 'DL_DGUV_ORTF'}), (m:Merkmal {id: 'MERK_ANLAGENALTER'})
MERGE (dl)-[:ERFORDERT_MERKMAL {prioritaet: 3}]->(m);

MATCH (na:Nutzungsart {id: 'NUTZ_BUERO'}), (pi:Pruefintervall {id: 'PI_4J'}), (dl:Dienstleistung {id: 'DL_DGUV_ORTF'})
MERGE (na)-[:BESTIMMT_INTERVALL {fuer_dl: dl.id}]->(pi);
MATCH (na:Nutzungsart {id: 'NUTZ_INDUSTRIE'}), (pi:Pruefintervall {id: 'PI_2J'}), (dl:Dienstleistung {id: 'DL_DGUV_ORTF'})
MERGE (na)-[:BESTIMMT_INTERVALL {fuer_dl: dl.id}]->(pi);


// ---------------------------------------------------------------------------
// EG-003: Aufzugsprüfung — Hauptprüfung
// ---------------------------------------------------------------------------
MERGE (dl_aufzug_hp:Dienstleistung {id: 'DL_AUFZUG_HP'})
SET dl_aufzug_hp.code = 'EG-003',
    dl_aufzug_hp.name = 'Aufzugsprüfung — Hauptprüfung',
    dl_aufzug_hp.kurz = 'Aufzug Hauptprüfung',
    dl_aufzug_hp.beschreibung = 'Wiederkehrende Hauptprüfung von Aufzugsanlagen als ZÜS nach BetrSichV',
    dl_aufzug_hp.kategorie = 'Fördertechnik';

MERGE (pp_aufzug_hp:Preisposition {id: 'PP_AUFZUG_HP'})
SET pp_aufzug_hp.name = 'Hauptprüfung pro Aufzug',
    pp_aufzug_hp.einheit = 'Aufzug',
    pp_aufzug_hp.bezugs_merkmal = 'anzahl_aufzuege',
    pp_aufzug_hp.basispreis = 385.00;

MERGE (pp_aufzug_hp_halt:Preisposition {id: 'PP_AUFZUG_HP_HALT'})
SET pp_aufzug_hp_halt.name = 'Zuschlag pro Haltestelle über 5',
    pp_aufzug_hp_halt.einheit = 'Haltestelle',
    pp_aufzug_hp_halt.bezugs_merkmal = 'anzahl_haltestellen',
    pp_aufzug_hp_halt.basispreis = 35.00,
    pp_aufzug_hp_halt.schwellwert = 5,
    pp_aufzug_hp_halt.schwellwert_logik = 'nur_ueber';

MATCH (dl:Dienstleistung {id: 'DL_AUFZUG_HP'}), (pp:Preisposition {id: 'PP_AUFZUG_HP'})
MERGE (dl)-[:HAT_PREISPOSITION {ist_basis: true}]->(pp);
MATCH (dl:Dienstleistung {id: 'DL_AUFZUG_HP'}), (pp:Preisposition {id: 'PP_AUFZUG_HP_HALT'})
MERGE (dl)-[:HAT_PREISPOSITION {ist_basis: false}]->(pp);

MERGE (st6:Staffel {id: 'ST_AUFZUG_HP_5'})
SET st6.ab_menge = 5, st6.preis = 350.00;
MERGE (st7:Staffel {id: 'ST_AUFZUG_HP_10'})
SET st7.ab_menge = 10, st7.preis = 320.00;

MATCH (pp:Preisposition {id: 'PP_AUFZUG_HP'}), (st:Staffel {id: 'ST_AUFZUG_HP_5'})
MERGE (pp)-[:HAT_STAFFEL]->(st);
MATCH (pp:Preisposition {id: 'PP_AUFZUG_HP'}), (st:Staffel {id: 'ST_AUFZUG_HP_10'})
MERGE (pp)-[:HAT_STAFFEL]->(st);

MATCH (dl:Dienstleistung {id: 'DL_AUFZUG_HP'}), (n:Norm {id: 'NORM_BETRSICHV'})
MERGE (dl)-[:BASIERT_AUF]->(n);
MATCH (dl:Dienstleistung {id: 'DL_AUFZUG_HP'}), (q:Qualifikation {id: 'QUAL_ZUES'})
MERGE (dl)-[:ERFORDERT_QUALIFIKATION]->(q);

MATCH (dl:Dienstleistung {id: 'DL_AUFZUG_HP'}), (m:Merkmal {id: 'MERK_AUFZUEGE'})
MERGE (dl)-[:ERFORDERT_MERKMAL {prioritaet: 1}]->(m);
MATCH (dl:Dienstleistung {id: 'DL_AUFZUG_HP'}), (m:Merkmal {id: 'MERK_HALTESTELLEN'})
MERGE (dl)-[:ERFORDERT_MERKMAL {prioritaet: 2}]->(m);
MATCH (dl:Dienstleistung {id: 'DL_AUFZUG_HP'}), (m:Merkmal {id: 'MERK_AUFZUGTYP'})
MERGE (dl)-[:ERFORDERT_MERKMAL {prioritaet: 3}]->(m);
MATCH (dl:Dienstleistung {id: 'DL_AUFZUG_HP'}), (m:Merkmal {id: 'MERK_TRAGLAST'})
MERGE (dl)-[:ERFORDERT_MERKMAL {prioritaet: 4}]->(m);


// ---------------------------------------------------------------------------
// EG-004: Aufzugsprüfung — Zwischenprüfung
// ---------------------------------------------------------------------------
MERGE (dl_aufzug_zp:Dienstleistung {id: 'DL_AUFZUG_ZP'})
SET dl_aufzug_zp.code = 'EG-004',
    dl_aufzug_zp.name = 'Aufzugsprüfung — Zwischenprüfung',
    dl_aufzug_zp.kurz = 'Aufzug Zwischenprüfung',
    dl_aufzug_zp.beschreibung = 'Zwischenprüfung zwischen den Hauptprüfungen nach BetrSichV',
    dl_aufzug_zp.kategorie = 'Fördertechnik';

MERGE (pp_aufzug_zp:Preisposition {id: 'PP_AUFZUG_ZP'})
SET pp_aufzug_zp.name = 'Zwischenprüfung pro Aufzug',
    pp_aufzug_zp.einheit = 'Aufzug',
    pp_aufzug_zp.bezugs_merkmal = 'anzahl_aufzuege',
    pp_aufzug_zp.basispreis = 245.00;

MATCH (dl:Dienstleistung {id: 'DL_AUFZUG_ZP'}), (pp:Preisposition {id: 'PP_AUFZUG_ZP'})
MERGE (dl)-[:HAT_PREISPOSITION]->(pp);

MERGE (st8:Staffel {id: 'ST_AUFZUG_ZP_5'})
SET st8.ab_menge = 5, st8.preis = 220.00;
MERGE (st9:Staffel {id: 'ST_AUFZUG_ZP_10'})
SET st9.ab_menge = 10, st9.preis = 195.00;

MATCH (pp:Preisposition {id: 'PP_AUFZUG_ZP'}), (st:Staffel {id: 'ST_AUFZUG_ZP_5'})
MERGE (pp)-[:HAT_STAFFEL]->(st);
MATCH (pp:Preisposition {id: 'PP_AUFZUG_ZP'}), (st:Staffel {id: 'ST_AUFZUG_ZP_10'})
MERGE (pp)-[:HAT_STAFFEL]->(st);

MATCH (dl:Dienstleistung {id: 'DL_AUFZUG_ZP'}), (n:Norm {id: 'NORM_BETRSICHV'})
MERGE (dl)-[:BASIERT_AUF]->(n);
MATCH (dl:Dienstleistung {id: 'DL_AUFZUG_ZP'}), (q:Qualifikation {id: 'QUAL_ZUES'})
MERGE (dl)-[:ERFORDERT_QUALIFIKATION]->(q);

MATCH (dl:Dienstleistung {id: 'DL_AUFZUG_ZP'}), (m:Merkmal {id: 'MERK_AUFZUEGE'})
MERGE (dl)-[:ERFORDERT_MERKMAL {prioritaet: 1}]->(m);


// ---------------------------------------------------------------------------
// EG-005: Brandmeldeanlage (BMA)
// ---------------------------------------------------------------------------
MERGE (dl_bma:Dienstleistung {id: 'DL_BMA'})
SET dl_bma.code = 'EG-005',
    dl_bma.name = 'Prüfung Brandmeldeanlage (BMA)',
    dl_bma.kurz = 'BMA-Prüfung',
    dl_bma.beschreibung = 'Wiederkehrende Prüfung der Brandmeldeanlage durch Prüfsachverständigen nach DIN 14675 / LBO',
    dl_bma.kategorie = 'Brandschutz';

MERGE (pp_bma_grund:Preisposition {id: 'PP_BMA_GRUND'})
SET pp_bma_grund.name = 'Grundpauschale BMA-Prüfung',
    pp_bma_grund.einheit = 'pauschal',
    pp_bma_grund.basispreis = 450.00;

MERGE (pp_bma_melder:Preisposition {id: 'PP_BMA_MELDER'})
SET pp_bma_melder.name = 'Prüfung pro Melder',
    pp_bma_melder.einheit = 'Melder',
    pp_bma_melder.bezugs_merkmal = 'anzahl_melder',
    pp_bma_melder.basispreis = 8.50;

MERGE (pp_bma_saa:Preisposition {id: 'PP_BMA_SAA'})
SET pp_bma_saa.name = 'Zuschlag Sprachalarmanlage (SAA)',
    pp_bma_saa.einheit = 'pauschal',
    pp_bma_saa.basispreis = 380.00,
    pp_bma_saa.bedingung = 'hat_sprachalarm = true';

MATCH (dl:Dienstleistung {id: 'DL_BMA'}), (pp:Preisposition {id: 'PP_BMA_GRUND'})
MERGE (dl)-[:HAT_PREISPOSITION {ist_basis: true}]->(pp);
MATCH (dl:Dienstleistung {id: 'DL_BMA'}), (pp:Preisposition {id: 'PP_BMA_MELDER'})
MERGE (dl)-[:HAT_PREISPOSITION {ist_basis: true}]->(pp);
MATCH (dl:Dienstleistung {id: 'DL_BMA'}), (pp:Preisposition {id: 'PP_BMA_SAA'})
MERGE (dl)-[:HAT_PREISPOSITION {ist_basis: false}]->(pp);

MERGE (st10:Staffel {id: 'ST_BMA_MELDER_200'})
SET st10.ab_menge = 200, st10.preis = 7.20;
MERGE (st11:Staffel {id: 'ST_BMA_MELDER_500'})
SET st11.ab_menge = 500, st11.preis = 6.00;

MATCH (pp:Preisposition {id: 'PP_BMA_MELDER'}), (st:Staffel {id: 'ST_BMA_MELDER_200'})
MERGE (pp)-[:HAT_STAFFEL]->(st);
MATCH (pp:Preisposition {id: 'PP_BMA_MELDER'}), (st:Staffel {id: 'ST_BMA_MELDER_500'})
MERGE (pp)-[:HAT_STAFFEL]->(st);

MATCH (dl:Dienstleistung {id: 'DL_BMA'}), (n:Norm {id: 'NORM_DIN14675'})
MERGE (dl)-[:BASIERT_AUF]->(n);
MATCH (dl:Dienstleistung {id: 'DL_BMA'}), (n:Norm {id: 'NORM_VDE0833'})
MERGE (dl)-[:BASIERT_AUF]->(n);
MATCH (dl:Dienstleistung {id: 'DL_BMA'}), (n:Norm {id: 'NORM_LBO'})
MERGE (dl)-[:BASIERT_AUF]->(n);
MATCH (dl:Dienstleistung {id: 'DL_BMA'}), (q:Qualifikation {id: 'QUAL_PSV'})
MERGE (dl)-[:ERFORDERT_QUALIFIKATION]->(q);

MATCH (dl:Dienstleistung {id: 'DL_BMA'}), (m:Merkmal {id: 'MERK_MELDER'})
MERGE (dl)-[:ERFORDERT_MERKMAL {prioritaet: 1}]->(m);
MATCH (dl:Dienstleistung {id: 'DL_BMA'}), (m:Merkmal {id: 'MERK_MELDER_TYP'})
MERGE (dl)-[:ERFORDERT_MERKMAL {prioritaet: 2}]->(m);
MATCH (dl:Dienstleistung {id: 'DL_BMA'}), (m:Merkmal {id: 'MERK_BMA_ZENTRALE'})
MERGE (dl)-[:ERFORDERT_MERKMAL {prioritaet: 3}]->(m);
MATCH (dl:Dienstleistung {id: 'DL_BMA'}), (m:Merkmal {id: 'MERK_SAA'})
MERGE (dl)-[:ERFORDERT_MERKMAL {prioritaet: 4}]->(m);


// ---------------------------------------------------------------------------
// EG-006: Blitzschutzanlage
// ---------------------------------------------------------------------------
MERGE (dl_blitz:Dienstleistung {id: 'DL_BLITZ'})
SET dl_blitz.code = 'EG-006',
    dl_blitz.name = 'Prüfung Blitzschutzanlage',
    dl_blitz.kurz = 'Blitzschutz-Prüfung',
    dl_blitz.beschreibung = 'Wiederkehrende Prüfung des äußeren und inneren Blitzschutzes nach DIN EN 62305',
    dl_blitz.kategorie = 'Gebäudeschutz';

MERGE (pp_blitz:Preisposition {id: 'PP_BLITZ'})
SET pp_blitz.name = 'Prüfung pro Anlage',
    pp_blitz.einheit = 'Anlage',
    pp_blitz.basispreis = 280.00;

MERGE (pp_blitz_abl:Preisposition {id: 'PP_BLITZ_ABL'})
SET pp_blitz_abl.name = 'Zusatz pro Ableitung über 8',
    pp_blitz_abl.einheit = 'Ableitung',
    pp_blitz_abl.bezugs_merkmal = 'anzahl_ableitungen',
    pp_blitz_abl.basispreis = 18.00,
    pp_blitz_abl.schwellwert = 8,
    pp_blitz_abl.schwellwert_logik = 'nur_ueber';

MATCH (dl:Dienstleistung {id: 'DL_BLITZ'}), (pp:Preisposition {id: 'PP_BLITZ'})
MERGE (dl)-[:HAT_PREISPOSITION {ist_basis: true}]->(pp);
MATCH (dl:Dienstleistung {id: 'DL_BLITZ'}), (pp:Preisposition {id: 'PP_BLITZ_ABL'})
MERGE (dl)-[:HAT_PREISPOSITION {ist_basis: false}]->(pp);

MATCH (dl:Dienstleistung {id: 'DL_BLITZ'}), (n:Norm {id: 'NORM_DIN62305'})
MERGE (dl)-[:BASIERT_AUF]->(n);
MATCH (dl:Dienstleistung {id: 'DL_BLITZ'}), (q:Qualifikation {id: 'QUAL_BEFP'})
MERGE (dl)-[:ERFORDERT_QUALIFIKATION]->(q);

MATCH (dl:Dienstleistung {id: 'DL_BLITZ'}), (m:Merkmal {id: 'MERK_ABLEITUNGEN'})
MERGE (dl)-[:ERFORDERT_MERKMAL {prioritaet: 1}]->(m);
MATCH (dl:Dienstleistung {id: 'DL_BLITZ'}), (m:Merkmal {id: 'MERK_BLITZSCHUTZKLASSE'})
MERGE (dl)-[:ERFORDERT_MERKMAL {prioritaet: 2}]->(m);

// Nutzungsart → Prüfintervall Blitzschutz
MATCH (na:Nutzungsart {id: 'NUTZ_OEFFENTLICH'}), (pi:Pruefintervall {id: 'PI_2J'}), (dl:Dienstleistung {id: 'DL_BLITZ'})
MERGE (na)-[:BESTIMMT_INTERVALL {fuer_dl: dl.id}]->(pi);
MATCH (na:Nutzungsart {id: 'NUTZ_BUERO'}), (pi:Pruefintervall {id: 'PI_4J'}), (dl:Dienstleistung {id: 'DL_BLITZ'})
MERGE (na)-[:BESTIMMT_INTERVALL {fuer_dl: dl.id}]->(pi);


// ---------------------------------------------------------------------------
// EG-007: E-Ladesäulen / Wallbox
// ---------------------------------------------------------------------------
MERGE (dl_wallbox:Dienstleistung {id: 'DL_WALLBOX'})
SET dl_wallbox.code = 'EG-007',
    dl_wallbox.name = 'Prüfung E-Ladesäulen / Wallbox',
    dl_wallbox.kurz = 'Wallbox-Prüfung',
    dl_wallbox.beschreibung = 'Wiederkehrende Prüfung von E-Ladeinfrastruktur nach DGUV V3',
    dl_wallbox.kategorie = 'Elektromobilität';

MERGE (pp_wallbox:Preisposition {id: 'PP_WALLBOX_LP'})
SET pp_wallbox.name = 'Prüfung pro Ladepunkt',
    pp_wallbox.einheit = 'Ladepunkt',
    pp_wallbox.bezugs_merkmal = 'anzahl_ladepunkte',
    pp_wallbox.basispreis = 145.00;

MERGE (pp_wallbox_dc:Preisposition {id: 'PP_WALLBOX_DC'})
SET pp_wallbox_dc.name = 'DC-Schnelllader Zuschlag',
    pp_wallbox_dc.einheit = 'Ladepunkt',
    pp_wallbox_dc.bezugs_merkmal = 'anzahl_ladepunkte',
    pp_wallbox_dc.basispreis = 95.00,
    pp_wallbox_dc.bedingung = 'ladetyp = DC';

MATCH (dl:Dienstleistung {id: 'DL_WALLBOX'}), (pp:Preisposition {id: 'PP_WALLBOX_LP'})
MERGE (dl)-[:HAT_PREISPOSITION {ist_basis: true}]->(pp);
MATCH (dl:Dienstleistung {id: 'DL_WALLBOX'}), (pp:Preisposition {id: 'PP_WALLBOX_DC'})
MERGE (dl)-[:HAT_PREISPOSITION {ist_basis: false}]->(pp);

MERGE (st12:Staffel {id: 'ST_WALLBOX_10'})
SET st12.ab_menge = 10, st12.preis = 125.00;
MERGE (st13:Staffel {id: 'ST_WALLBOX_25'})
SET st13.ab_menge = 25, st13.preis = 110.00;
MERGE (st14:Staffel {id: 'ST_WALLBOX_50'})
SET st14.ab_menge = 50, st14.preis = 95.00;

MATCH (pp:Preisposition {id: 'PP_WALLBOX_LP'}), (st:Staffel {id: 'ST_WALLBOX_10'})
MERGE (pp)-[:HAT_STAFFEL]->(st);
MATCH (pp:Preisposition {id: 'PP_WALLBOX_LP'}), (st:Staffel {id: 'ST_WALLBOX_25'})
MERGE (pp)-[:HAT_STAFFEL]->(st);
MATCH (pp:Preisposition {id: 'PP_WALLBOX_LP'}), (st:Staffel {id: 'ST_WALLBOX_50'})
MERGE (pp)-[:HAT_STAFFEL]->(st);

MATCH (dl:Dienstleistung {id: 'DL_WALLBOX'}), (n:Norm {id: 'NORM_DGUV3'})
MERGE (dl)-[:BASIERT_AUF]->(n);
MATCH (dl:Dienstleistung {id: 'DL_WALLBOX'}), (n:Norm {id: 'NORM_VDE0100'})
MERGE (dl)-[:BASIERT_AUF]->(n);
MATCH (dl:Dienstleistung {id: 'DL_WALLBOX'}), (q:Qualifikation {id: 'QUAL_EFK'})
MERGE (dl)-[:ERFORDERT_QUALIFIKATION]->(q);

MATCH (dl:Dienstleistung {id: 'DL_WALLBOX'}), (m:Merkmal {id: 'MERK_LADEPUNKTE'})
MERGE (dl)-[:ERFORDERT_MERKMAL {prioritaet: 1}]->(m);
MATCH (dl:Dienstleistung {id: 'DL_WALLBOX'}), (m:Merkmal {id: 'MERK_LADETYP'})
MERGE (dl)-[:ERFORDERT_MERKMAL {prioritaet: 2}]->(m);
MATCH (dl:Dienstleistung {id: 'DL_WALLBOX'}), (m:Merkmal {id: 'MERK_LADELEISTUNG'})
MERGE (dl)-[:ERFORDERT_MERKMAL {prioritaet: 3}]->(m);


// ---------------------------------------------------------------------------
// EG-008: Photovoltaik-Anlage
// ---------------------------------------------------------------------------
MERGE (dl_pv:Dienstleistung {id: 'DL_PV'})
SET dl_pv.code = 'EG-008',
    dl_pv.name = 'Prüfung Photovoltaik-Anlage',
    dl_pv.kurz = 'PV-Prüfung',
    dl_pv.beschreibung = 'Erst- und Wiederholungsprüfung von PV-Anlagen — Anlagensicherheit, Schutzeinrichtungen, Isolationswiderstand',
    dl_pv.kategorie = 'Erneuerbare Energien';

MERGE (pp_pv_grund:Preisposition {id: 'PP_PV_GRUND'})
SET pp_pv_grund.name = 'Grundpauschale PV-Prüfung',
    pp_pv_grund.einheit = 'pauschal',
    pp_pv_grund.basispreis = 450.00;

MERGE (pp_pv_kwp:Preisposition {id: 'PP_PV_KWP'})
SET pp_pv_kwp.name = 'Prüfung pro kWp',
    pp_pv_kwp.einheit = 'kWp',
    pp_pv_kwp.bezugs_merkmal = 'kwp',
    pp_pv_kwp.basispreis = 2.80;

MATCH (dl:Dienstleistung {id: 'DL_PV'}), (pp:Preisposition {id: 'PP_PV_GRUND'})
MERGE (dl)-[:HAT_PREISPOSITION {ist_basis: true}]->(pp);
MATCH (dl:Dienstleistung {id: 'DL_PV'}), (pp:Preisposition {id: 'PP_PV_KWP'})
MERGE (dl)-[:HAT_PREISPOSITION {ist_basis: true}]->(pp);

MERGE (st15:Staffel {id: 'ST_PV_KWP_100'})
SET st15.ab_menge = 100, st15.preis = 2.30;
MERGE (st16:Staffel {id: 'ST_PV_KWP_500'})
SET st16.ab_menge = 500, st16.preis = 1.80;

MATCH (pp:Preisposition {id: 'PP_PV_KWP'}), (st:Staffel {id: 'ST_PV_KWP_100'})
MERGE (pp)-[:HAT_STAFFEL]->(st);
MATCH (pp:Preisposition {id: 'PP_PV_KWP'}), (st:Staffel {id: 'ST_PV_KWP_500'})
MERGE (pp)-[:HAT_STAFFEL]->(st);

MATCH (dl:Dienstleistung {id: 'DL_PV'}), (n:Norm {id: 'NORM_VDE0100'})
MERGE (dl)-[:BASIERT_AUF]->(n);
MATCH (dl:Dienstleistung {id: 'DL_PV'}), (q:Qualifikation {id: 'QUAL_EFK'})
MERGE (dl)-[:ERFORDERT_QUALIFIKATION]->(q);

MATCH (dl:Dienstleistung {id: 'DL_PV'}), (m:Merkmal {id: 'MERK_KWP'})
MERGE (dl)-[:ERFORDERT_MERKMAL {prioritaet: 1}]->(m);
MATCH (dl:Dienstleistung {id: 'DL_PV'}), (m:Merkmal {id: 'MERK_MODULE'})
MERGE (dl)-[:ERFORDERT_MERKMAL {prioritaet: 2}]->(m);


// ---------------------------------------------------------------------------
// EG-009: Elektro-Thermografie
// ---------------------------------------------------------------------------
MERGE (dl_thermo:Dienstleistung {id: 'DL_THERMO'})
SET dl_thermo.code = 'EG-009',
    dl_thermo.name = 'Elektro-Thermografie',
    dl_thermo.kurz = 'Thermografie',
    dl_thermo.beschreibung = 'Thermografische Untersuchung elektrischer Schaltanlagen und Verteilungen zur Erkennung von Hot Spots',
    dl_thermo.kategorie = 'Elektrotechnik';

MERGE (pp_thermo:Preisposition {id: 'PP_THERMO'})
SET pp_thermo.name = 'Thermografie pro Schaltanlage/Verteilung',
    pp_thermo.einheit = 'Schaltanlage',
    pp_thermo.bezugs_merkmal = 'anzahl_schaltanlagen',
    pp_thermo.basispreis = 85.00;

MATCH (dl:Dienstleistung {id: 'DL_THERMO'}), (pp:Preisposition {id: 'PP_THERMO'})
MERGE (dl)-[:HAT_PREISPOSITION]->(pp);

MERGE (st17:Staffel {id: 'ST_THERMO_20'})
SET st17.ab_menge = 20, st17.preis = 72.00;
MERGE (st18:Staffel {id: 'ST_THERMO_50'})
SET st18.ab_menge = 50, st18.preis = 60.00;

MATCH (pp:Preisposition {id: 'PP_THERMO'}), (st:Staffel {id: 'ST_THERMO_20'})
MERGE (pp)-[:HAT_STAFFEL]->(st);
MATCH (pp:Preisposition {id: 'PP_THERMO'}), (st:Staffel {id: 'ST_THERMO_50'})
MERGE (pp)-[:HAT_STAFFEL]->(st);

MATCH (dl:Dienstleistung {id: 'DL_THERMO'}), (q:Qualifikation {id: 'QUAL_THERMO'})
MERGE (dl)-[:ERFORDERT_QUALIFIKATION]->(q);

MATCH (dl:Dienstleistung {id: 'DL_THERMO'}), (m:Merkmal {id: 'MERK_SCHALTANLAGEN'})
MERGE (dl)-[:ERFORDERT_MERKMAL {prioritaet: 1}]->(m);


// ---------------------------------------------------------------------------
// EG-010: Sprinkleranlage
// ---------------------------------------------------------------------------
MERGE (dl_sprinkler:Dienstleistung {id: 'DL_SPRINKLER'})
SET dl_sprinkler.code = 'EG-010',
    dl_sprinkler.name = 'Prüfung Sprinkleranlage',
    dl_sprinkler.kurz = 'Sprinkler-Prüfung',
    dl_sprinkler.beschreibung = 'Wiederkehrende Prüfung von Sprinkleranlagen durch Prüfsachverständigen nach VdS CEA 4001',
    dl_sprinkler.kategorie = 'Brandschutz';

MERGE (pp_sprinkler_grund:Preisposition {id: 'PP_SPRINKLER_GRUND'})
SET pp_sprinkler_grund.name = 'Grundpauschale Sprinklerprüfung',
    pp_sprinkler_grund.einheit = 'pauschal',
    pp_sprinkler_grund.basispreis = 650.00;

MERGE (pp_sprinkler_flaeche:Preisposition {id: 'PP_SPRINKLER_FLAECHE'})
SET pp_sprinkler_flaeche.name = 'Prüfung pro m² geschützte Fläche',
    pp_sprinkler_flaeche.einheit = 'm²',
    pp_sprinkler_flaeche.bezugs_merkmal = 'sprinklerflaeche_m2',
    pp_sprinkler_flaeche.basispreis = 0.45;

MATCH (dl:Dienstleistung {id: 'DL_SPRINKLER'}), (pp:Preisposition {id: 'PP_SPRINKLER_GRUND'})
MERGE (dl)-[:HAT_PREISPOSITION {ist_basis: true}]->(pp);
MATCH (dl:Dienstleistung {id: 'DL_SPRINKLER'}), (pp:Preisposition {id: 'PP_SPRINKLER_FLAECHE'})
MERGE (dl)-[:HAT_PREISPOSITION {ist_basis: true}]->(pp);

MERGE (st19:Staffel {id: 'ST_SPRINKLER_5000'})
SET st19.ab_menge = 5000, st19.preis = 0.38;
MERGE (st20:Staffel {id: 'ST_SPRINKLER_15000'})
SET st20.ab_menge = 15000, st20.preis = 0.30;

MATCH (pp:Preisposition {id: 'PP_SPRINKLER_FLAECHE'}), (st:Staffel {id: 'ST_SPRINKLER_5000'})
MERGE (pp)-[:HAT_STAFFEL]->(st);
MATCH (pp:Preisposition {id: 'PP_SPRINKLER_FLAECHE'}), (st:Staffel {id: 'ST_SPRINKLER_15000'})
MERGE (pp)-[:HAT_STAFFEL]->(st);

MATCH (dl:Dienstleistung {id: 'DL_SPRINKLER'}), (n:Norm {id: 'NORM_VDS_CEA'})
MERGE (dl)-[:BASIERT_AUF]->(n);
MATCH (dl:Dienstleistung {id: 'DL_SPRINKLER'}), (n:Norm {id: 'NORM_LBO'})
MERGE (dl)-[:BASIERT_AUF]->(n);
MATCH (dl:Dienstleistung {id: 'DL_SPRINKLER'}), (q:Qualifikation {id: 'QUAL_PSV'})
MERGE (dl)-[:ERFORDERT_QUALIFIKATION]->(q);

MATCH (dl:Dienstleistung {id: 'DL_SPRINKLER'}), (m:Merkmal {id: 'MERK_SPRINKLERFLAECHE'})
MERGE (dl)-[:ERFORDERT_MERKMAL {prioritaet: 1}]->(m);
MATCH (dl:Dienstleistung {id: 'DL_SPRINKLER'}), (m:Merkmal {id: 'MERK_SPRINKLERTYP'})
MERGE (dl)-[:ERFORDERT_MERKMAL {prioritaet: 2}]->(m);


// ---------------------------------------------------------------------------
// EG-011: RLT-Anlage (HVAC)
// ---------------------------------------------------------------------------
MERGE (dl_rlt:Dienstleistung {id: 'DL_RLT'})
SET dl_rlt.code = 'EG-011',
    dl_rlt.name = 'Prüfung Raumlufttechnische Anlage (RLT)',
    dl_rlt.kurz = 'RLT-Prüfung',
    dl_rlt.beschreibung = 'Prüfung von Lüftungs- und Klimaanlagen auf Hygiene und Betriebssicherheit',
    dl_rlt.kategorie = 'Gebäudetechnik';

MERGE (pp_rlt:Preisposition {id: 'PP_RLT'})
SET pp_rlt.name = 'Prüfung pro RLT-Anlage',
    pp_rlt.einheit = 'Anlage',
    pp_rlt.basispreis = 520.00;

MATCH (dl:Dienstleistung {id: 'DL_RLT'}), (pp:Preisposition {id: 'PP_RLT'})
MERGE (dl)-[:HAT_PREISPOSITION]->(pp);

MERGE (st21:Staffel {id: 'ST_RLT_3'})
SET st21.ab_menge = 3, st21.preis = 470.00;
MERGE (st22:Staffel {id: 'ST_RLT_10'})
SET st22.ab_menge = 10, st22.preis = 420.00;

MATCH (pp:Preisposition {id: 'PP_RLT'}), (st:Staffel {id: 'ST_RLT_3'})
MERGE (pp)-[:HAT_STAFFEL]->(st);
MATCH (pp:Preisposition {id: 'PP_RLT'}), (st:Staffel {id: 'ST_RLT_10'})
MERGE (pp)-[:HAT_STAFFEL]->(st);

MATCH (dl:Dienstleistung {id: 'DL_RLT'}), (n:Norm {id: 'NORM_DIN18232'})
MERGE (dl)-[:BASIERT_AUF]->(n);
MATCH (dl:Dienstleistung {id: 'DL_RLT'}), (q:Qualifikation {id: 'QUAL_BEFP'})
MERGE (dl)-[:ERFORDERT_QUALIFIKATION]->(q);


// =============================================================================
// CROSS-CUTTING RELATIONSHIPS — THE GRAPH MAGIC
// =============================================================================

// ---------------------------------------------------------------------------
// GLEICHE_BEGEHUNG — services that can share a site visit (→ Bündelrabatt)
// ---------------------------------------------------------------------------
// BMA + Sprinkler: both Brandschutz, same PSV can do both
MATCH (d1:Dienstleistung {id: 'DL_BMA'}), (d2:Dienstleistung {id: 'DL_SPRINKLER'})
MERGE (d1)-[:GLEICHE_BEGEHUNG {
    rabatt_prozent: 10.0,
    grund: 'Gleicher Prüfsachverständiger, gleicher Brandschutz-Bereich',
    min_ersparnis_h: 2.0
}]->(d2);

// DGUV V3 ortsfest + Thermografie: Thermografie ergänzt die Anlagenprüfung
MATCH (d1:Dienstleistung {id: 'DL_DGUV_ORTF'}), (d2:Dienstleistung {id: 'DL_THERMO'})
MERGE (d1)-[:GLEICHE_BEGEHUNG {
    rabatt_prozent: 15.0,
    grund: 'Thermografie während DGUV-Begehung — kein separater Termin nötig',
    min_ersparnis_h: 1.5
}]->(d2);

// DGUV V3 ortsfest + ortsveränderlich: gleicher Elektro-Bereich
MATCH (d1:Dienstleistung {id: 'DL_DGUV_ORTF'}), (d2:Dienstleistung {id: 'DL_DGUV_ORTV'})
MERGE (d1)-[:GLEICHE_BEGEHUNG {
    rabatt_prozent: 8.0,
    grund: 'Gleicher Standort, gleiche Elektrofachkraft vor Ort',
    min_ersparnis_h: 1.0
}]->(d2);

// Aufzug HP + ZP am gleichen Standort (multi-Aufzug: eine Anfahrt)
MATCH (d1:Dienstleistung {id: 'DL_AUFZUG_HP'}), (d2:Dienstleistung {id: 'DL_AUFZUG_ZP'})
MERGE (d1)-[:GLEICHE_BEGEHUNG {
    rabatt_prozent: 5.0,
    grund: 'HP und ZP verschiedener Aufzüge am gleichen Standort kombinierbar',
    min_ersparnis_h: 0.5
}]->(d2);

// BMA + Blitzschutz: oft am gleichen Sonderbau
MATCH (d1:Dienstleistung {id: 'DL_BMA'}), (d2:Dienstleistung {id: 'DL_BLITZ'})
MERGE (d1)-[:GLEICHE_BEGEHUNG {
    rabatt_prozent: 5.0,
    grund: 'Bei Sonderbauten oft gleiche Prüfperiode',
    min_ersparnis_h: 0.5
}]->(d2);

// Wallbox + DGUV V3: Wallbox IST eine ortsfeste Anlage
MATCH (d1:Dienstleistung {id: 'DL_WALLBOX'}), (d2:Dienstleistung {id: 'DL_DGUV_ORTF'})
MERGE (d1)-[:GLEICHE_BEGEHUNG {
    rabatt_prozent: 10.0,
    grund: 'Wallboxen werden bei DGUV V3 ortsfest oft mitgeprüft',
    min_ersparnis_h: 1.0
}]->(d2);

// PV + Blitzschutz: Blitzschutz-Anlage schützt PV, oft gemeinsam geprüft
MATCH (d1:Dienstleistung {id: 'DL_PV'}), (d2:Dienstleistung {id: 'DL_BLITZ'})
MERGE (d1)-[:GLEICHE_BEGEHUNG {
    rabatt_prozent: 8.0,
    grund: 'Äußerer Blitzschutz und PV-Anlage auf gleichem Dach',
    min_ersparnis_h: 1.0
}]->(d2);


// ---------------------------------------------------------------------------
// SCHLIESST_EIN — one service includes/subsumes another
// ---------------------------------------------------------------------------
// DGUV V3 ortsfest schließt Thermografie ein (wenn gewünscht)
MATCH (d1:Dienstleistung {id: 'DL_DGUV_ORTF'}), (d2:Dienstleistung {id: 'DL_THERMO'})
MERGE (d1)-[:SCHLIESST_EIN {
    typ: 'optional_addon',
    beschreibung: 'Thermografie kann als Zusatzleistung bei DGUV-Begehung erfolgen'
}]->(d2);


// ---------------------------------------------------------------------------
// EMPFIEHLT — cross-sell / upsell suggestions
// ---------------------------------------------------------------------------
// Wallbox → empfiehlt PV (Synergie E-Mobilität + PV)
MATCH (d1:Dienstleistung {id: 'DL_WALLBOX'}), (d2:Dienstleistung {id: 'DL_PV'})
MERGE (d1)-[:EMPFIEHLT {
    grund: 'PV-Anlage speist Wallboxen — gemeinsame Prüfung spart Kosten',
    relevanz: 'hoch'
}]->(d2);

// BMA → empfiehlt RLT (Rauchableitung + Lüftung)
MATCH (d1:Dienstleistung {id: 'DL_BMA'}), (d2:Dienstleistung {id: 'DL_RLT'})
MERGE (d1)-[:EMPFIEHLT {
    grund: 'RLT-Anlagen sind Teil des Entrauchungskonzepts',
    relevanz: 'mittel'
}]->(d2);

// BMA → empfiehlt Sprinkler
MATCH (d1:Dienstleistung {id: 'DL_BMA'}), (d2:Dienstleistung {id: 'DL_SPRINKLER'})
MERGE (d1)-[:EMPFIEHLT {
    grund: 'Ganzheitliches Brandschutzkonzept: Detektion + Löschung',
    relevanz: 'hoch'
}]->(d2);

// DGUV V3 ortsfest → empfiehlt Blitzschutz
MATCH (d1:Dienstleistung {id: 'DL_DGUV_ORTF'}), (d2:Dienstleistung {id: 'DL_BLITZ'})
MERGE (d1)-[:EMPFIEHLT {
    grund: 'Überspannungsschutz ist Teil des elektrischen Schutzkonzepts',
    relevanz: 'mittel'
}]->(d2);

// Aufzug → empfiehlt DGUV V3 (Aufzug hat elektrische Anlage)
MATCH (d1:Dienstleistung {id: 'DL_AUFZUG_HP'}), (d2:Dienstleistung {id: 'DL_DGUV_ORTF'})
MERGE (d1)-[:EMPFIEHLT {
    grund: 'Aufzugsanlage enthält elektrische Steuerung — DGUV V3 Prüfpflicht',
    relevanz: 'hoch'
}]->(d2);


// ---------------------------------------------------------------------------
// GEBÄUDETYP → PFLICHT-DIENSTLEISTUNG (mandatory inspections)
// ---------------------------------------------------------------------------
// Sonderbauten nach LBO → BMA Pflicht
MATCH (gt:Gebaeudetyp {id: 'GT_KRANKENHAUS'}), (dl:Dienstleistung {id: 'DL_BMA'})
MERGE (gt)-[:ERFORDERT_PRUEFUNG {pflicht: true, grund: 'Sonderbau nach LBO'}]->(dl);
MATCH (gt:Gebaeudetyp {id: 'GT_HOTEL'}), (dl:Dienstleistung {id: 'DL_BMA'})
MERGE (gt)-[:ERFORDERT_PRUEFUNG {pflicht: true, grund: 'Beherbergungsstätte > 12 Betten'}]->(dl);
MATCH (gt:Gebaeudetyp {id: 'GT_VERSAMM'}), (dl:Dienstleistung {id: 'DL_BMA'})
MERGE (gt)-[:ERFORDERT_PRUEFUNG {pflicht: true, grund: 'Versammlungsstätte > 200 Personen'}]->(dl);
MATCH (gt:Gebaeudetyp {id: 'GT_HOCHHAUS'}), (dl:Dienstleistung {id: 'DL_BMA'})
MERGE (gt)-[:ERFORDERT_PRUEFUNG {pflicht: true, grund: 'Hochhaus > 22m'}]->(dl);
MATCH (gt:Gebaeudetyp {id: 'GT_HANDEL'}), (dl:Dienstleistung {id: 'DL_BMA'})
MERGE (gt)-[:ERFORDERT_PRUEFUNG {pflicht: true, grund: 'Verkaufsstätte > 2000m²'}]->(dl);

// Hochhaus → Feuerwehraufzug Pflicht
MATCH (gt:Gebaeudetyp {id: 'GT_HOCHHAUS'}), (dl:Dienstleistung {id: 'DL_AUFZUG_HP'})
MERGE (gt)-[:ERFORDERT_PRUEFUNG {pflicht: true, grund: 'Feuerwehraufzug Pflicht bei Hochhäusern'}]->(dl);

// Hochhaus → Sprinkler oft Pflicht
MATCH (gt:Gebaeudetyp {id: 'GT_HOCHHAUS'}), (dl:Dienstleistung {id: 'DL_SPRINKLER'})
MERGE (gt)-[:ERFORDERT_PRUEFUNG {pflicht: true, grund: 'Sprinkleranlage bei Hochhäusern > 60m'}]->(dl);

// Sonderbauten → Blitzschutz
MATCH (gt:Gebaeudetyp {id: 'GT_KRANKENHAUS'}), (dl:Dienstleistung {id: 'DL_BLITZ'})
MERGE (gt)-[:ERFORDERT_PRUEFUNG {pflicht: true, grund: 'Blitzschutz Klasse I für Krankenhäuser'}]->(dl);

// Alle Gebäude → DGUV V3 (Arbeitsstätte = Pflicht)
MATCH (gt:Gebaeudetyp {id: 'GT_BUERO'}), (dl:Dienstleistung {id: 'DL_DGUV_ORTV'})
MERGE (gt)-[:ERFORDERT_PRUEFUNG {pflicht: true, grund: 'DGUV V3 Pflicht für alle Arbeitsstätten'}]->(dl);
MATCH (gt:Gebaeudetyp {id: 'GT_INDUSTRIE'}), (dl:Dienstleistung {id: 'DL_DGUV_ORTV'})
MERGE (gt)-[:ERFORDERT_PRUEFUNG {pflicht: true, grund: 'DGUV V3 Pflicht für alle Arbeitsstätten'}]->(dl);
MATCH (gt:Gebaeudetyp {id: 'GT_HANDEL'}), (dl:Dienstleistung {id: 'DL_DGUV_ORTV'})
MERGE (gt)-[:ERFORDERT_PRUEFUNG {pflicht: true, grund: 'DGUV V3 Pflicht für alle Arbeitsstätten'}]->(dl);

// Lager → Sprinkler
MATCH (gt:Gebaeudetyp {id: 'GT_LAGER'}), (dl:Dienstleistung {id: 'DL_SPRINKLER'})
MERGE (gt)-[:ERFORDERT_PRUEFUNG {pflicht: true, grund: 'Sprinkleranlage für Lager > 1600m² nach IndBauRL'}]->(dl);


// ---------------------------------------------------------------------------
// ANFAHRTSPAUSCHALEN — shared across all services at a Standort
// ---------------------------------------------------------------------------
MERGE (pp_anfahrt_nah:Preisposition {id: 'PP_ANFAHRT_NAH'})
SET pp_anfahrt_nah.name = 'Anfahrtspauschale bis 50 km',
    pp_anfahrt_nah.einheit = 'pauschal',
    pp_anfahrt_nah.basispreis = 85.00,
    pp_anfahrt_nah.bedingung = 'entfernung_km <= 50',
    pp_anfahrt_nah.ist_anfahrt = true;

MERGE (pp_anfahrt_mittel:Preisposition {id: 'PP_ANFAHRT_MITTEL'})
SET pp_anfahrt_mittel.name = 'Anfahrtspauschale 50-100 km',
    pp_anfahrt_mittel.einheit = 'pauschal',
    pp_anfahrt_mittel.basispreis = 145.00,
    pp_anfahrt_mittel.bedingung = 'entfernung_km > 50 AND entfernung_km <= 100',
    pp_anfahrt_mittel.ist_anfahrt = true;

MERGE (pp_anfahrt_fern:Preisposition {id: 'PP_ANFAHRT_FERN'})
SET pp_anfahrt_fern.name = 'Anfahrtspauschale über 100 km',
    pp_anfahrt_fern.einheit = 'pauschal',
    pp_anfahrt_fern.basispreis = 220.00,
    pp_anfahrt_fern.bedingung = 'entfernung_km > 100',
    pp_anfahrt_fern.ist_anfahrt = true;

// Anfahrt wird GETEILT wenn GLEICHE_BEGEHUNG
// → Engine-Logik: Anfahrt 1× berechnen, auf alle DL am Standort aufteilen
// → Das ist Graph-Logik, nicht hardcoded!


// =============================================================================
// GRAPH STATISTICS (Expected after seeding)
// =============================================================================
// Node types:     14 (+ Stressor, Trait)
// Nodes:          ~130
// Relationships:  ~210+
// Relationship types: 17 (+ EXPOSES_TO, DEMANDS_TRAIT, AFFECTS)
//
// STRESSOR/TRAIT LAYER (engine-compatible labels from graph project):
//   - 12 Stressor nodes (domain_label: "Kostentreiber")
//   - 9 Trait nodes (domain_label: "Effekt")
//   - ~15 EXPOSES_TO edges (Context → Stressor)
//   - ~25 DEMANDS_TRAIT edges (Stressor → Trait)
//   - ~15 AFFECTS edges (Stressor → Dienstleistung)
//
// KEY CAUSAL CHAINS (agent traverses to explain WHY):
//   Krankenhaus →EXPOSES_TO→ KT_SONDERBAU →DEMANDS_TRAIT→ kürzeres Intervall + PSV + Pflicht-BMA
//   Krankenhaus →EXPOSES_TO→ KT_MEDIZIN →DEMANDS_TRAIT→ +25% Zuschlag + Spezialgerät
//   Tiefgarage →LOEST_AUS→ ATEX →EXPOSES_TO→ KT_EXPLOSIONSSCHUTZ →DEMANDS_TRAIT→ +35%
//   Anlagenalter>25 →EXPOSES_TO→ KT_ALTANLAGE →DEMANDS_TRAIT→ +20% + erweiterte Doku
//   Hohe Stückzahl →EXPOSES_TO→ KT_HOHE_STUECKZAHL →DEMANDS_TRAIT→ Staffelrabatt
//
// CROSS-CUTTING (Stressor shared across services via AFFECTS):
//   - KT_SONDERBAU affects 4 services (BMA, Sprinkler, Blitz, Aufzug)
//   - KT_EXPLOSIONSSCHUTZ affects 2 services (Wallbox, DGUV ortf.)
//   - KT_ALTANLAGE affects 2 services (DGUV ortf., Thermografie)
//   - KT_MEDIZIN affects 2 services (DGUV ortf., BMA)
