---
quelle: VdS-Nutzungsartenliste (Screenshots Piotr, aus Call) — To-Do #4 erledigt
typ: taxonomie / pricing_routing
kontext: VdS 2871 Branchen-Code — Pflichtangabe im Prüfbericht (100% Fill-Rate)
verwandt: [[data_pausch_ma505_branchen]]
---

# VdS-2871 Branchen-Code / Nutzungsarten (Pflichtangabe Prüfbericht)

Offizielle VdS-Klassifikation, die in **jedem** VdS-Prüfbericht steht (Pflichtfeld) → im
Gegensatz zu m² (0% Fill) ein **zuverlässig extrahierbares Merkmal**.

## Vollständige Liste (transkribiert)

| Code | Branche/Nutzung |
|---|---|
| 0001 | Bürogebäude, Immobilienverwaltung |
| 0002 | Lager, Siloanlagen |
| 0004 | Laboratorien, Dauerversuchsräume |
| 0005 | Rechenzentren |
| 0008 | Dienstleistungsbetriebe |
| 0100 | Grundstoffindustrie (Erze, Kohle usw.) |
| 0201 | Steinbrüche/Gruben z.B. Kies, Sand, Ton |
| 0202 | Herstellung von Zement, Kalk, Gips, feuerfesten Materialien |
| 0203 | Keramik, Glas, Ziegel |
| 0204 | Bauindustrie, Baustoffe, Bauteile, Baustellen |
| 0205 | Bitumen-Mischanlagen, Teersplitt |
| 0300 | Metallverarbeitung |
| 0306 | Elektrotechnische Betriebe |
| 0400 | Chemie, Kunststoffherstellung (inklusive Tankstellen, Tanklager) |
| 0401 | Kunststoffverarbeitung |
| 0500 | Textil (inklusive Wäschereien) |
| 0600 | Leder, Papier (inklusive Druckereien) |
| 0700 | Holz |
| 0800 | Nahrungs- und Genussmittel (inklusive Kühlhäuser) |
| 0901 | Versammlungsstätten |
| 0902 | Hotel- und Gaststättenbetriebe, Kantinen |
| 0903 | Bars und Diskotheken |
| 0904 | Kauf- und Warenhäuser, Einkaufszentren usw. |
| 0905 | Sanatorien, Krankenhäuser, Pflege- und Kinderheime, Kindertagesstätten |
| 0906 | Parkhäuser, Garagen |
| 0907 | Intensivtierhaltung |
| 0908 | Land- und Forstwirtschaft, Gartenbaubetriebe |
| 0909 | öffentliche Ver- und Entsorgungsbetriebe |

## Mapping-Vorschlag → unser Modell (Branche → Enum + Kat)

> ⚠️ **WICHTIG — zwei getrennte Taxonomien, nicht vermischen:**
> Der **Komplexitätsfaktor** kommt aus einer **separaten** Liste (NetInform „Technischer
> Ausstattungsgrad", 7 grobe Immobilien-Typen) und ist auf unserem `GebaeudeNutzungDGUV`-Enum
> verschlüsselt (bereits implementiert, Commit 6cc0616). Er wird **NICHT** aus dem VdS-Branchen-Code
> abgeleitet — das ginge gar nicht: z.B. VdS **0905** (Krankenhäuser + Pflege + Kitas) spannt drei
> NetInform-Buckets (Krankenhaus 2,0 / Betreuung 1,5 / Lehranstalten 2,0), und schwere Industrie
> (0100–0800) hat dort gar keinen Bucket außer „Logistik 1,0".
> **Aufgabenteilung:** NetInform/Enum → **Faktor** · VdS-Branchen-Code → **Installationskategorie + Routing**.
> Die Faktor-Spalte unten ist nur eine grobe Quer-Referenz über das Enum, NICHT der Mechanismus.

**Status: implementiert** (Commit d358bd7) — Branche-Begriffe → Kat in `NUTZUNG_ZU_KATEGORIE`.
`?` = Kategorie-Zuordnung offen, von S. Pausch zu bestätigen (Fr 20.06.).

| Code | → GebaeudeNutzungDGUV | Kat (Vorschlag) | Komplex-Faktor | Bezug Test |
|---|---|---|---|---|
| 0001 | BUEROGEBAEUDE | 2 | 1,0 Büro | T08, T15 |
| 0002 | INDUSTRIE (lager) | 2 | 1,0 Logistik | — |
| 0004 | INDUSTRIE (labor) | 2–4 ? | — | — |
| 0005 | INDUSTRIE (Rechenzentrum) | ? | — | T10 Max Planck |
| 0008 | SERVICE_CENTER | 2 | 1,0 | — |
| 0100–0205 | INDUSTRIE | 3 | 1,0 | — |
| 0300 | INDUSTRIE (Metall) | 3 | 1,0 | **Test 7 Metallverarb., ZF** |
| 0306 | INDUSTRIE | 3 | 1,0 | — |
| 0400/0401 | INDUSTRIE (Chemie/Kunststoff) | 3+ ? | 1,0 | — |
| 0500/0600/0700 | INDUSTRIE | 3 | 1,0 | — |
| **0800** | **INDUSTRIE (Nahrungsmittel)** | **2 ODER 3 ⚠️** | 1,0 | **T01 Hipp — DIE offene Kat-Frage!** |
| 0901 | VERSAMMLUNGSSTAETTE | 3 ? | 1,25 (Legacy) | — |
| 0902 | HOTEL | 2 | 1,5 Hotel | Test 6 Maritim, T13 Motel One |
| 0903 | VERSAMMLUNGSSTAETTE | 3 ? | 1,5 ? | — |
| **0904** | **VERKAUFSSTAETTE** | **3** | 1,5 Misch | **Test 2/11 REWE** |
| **0905** | **KRANKENHAUS / SENIORENTREFF / SCHULE** (Sammelcode!) | Mix 2+7 | 2,0 Krankenhaus | **T12 Helios, T14 roMEd** |
| 0906 | TIEFGARAGE | 1 | 1,0 (LPV) | — |
| 0907 | INDUSTRIE (Tierhaltung) | ? | — | T05-nah |
| 0908 | INDUSTRIE (Land-/Forstw.) | ? | — | **Test 5 Landwirt** |
| 0909 | INDUSTRIE (Ver-/Entsorgung) | ? | — | — |

## Was das für uns bringt (Verwendung)

1. **Autoritative Nutzungs-Taxonomie** statt ad-hoc Keyword-Matching in `NUTZUNG_ZU_KATEGORIE`.
   Reduziert direkt den in der Extraktions-Diagnose gemessenen **Kat-Misclassification-Drift**
   (T02 Kat 2 vs 3, T12 Kat 6 vs 7 → 0–16% Preisdivergenz).
2. **Zuverlässiges Feature für Industrie/ZF**: Branchen-Code ist Pflichtangabe (100% Fill),
   wo m² fehlt → Join-/Routing-Schlüssel für die ZF-Prüfberichte.
3. **Verankert mehrere offene Fragen an einer offiziellen Quelle:** 0800=T01 Kat-Frage,
   0904=REWE-Routing, 0905=Krankenhaus-Mix, 0902=Hotel.

## Offen für S. Pausch (Fr 20.06.) — nur die Kat-Zuordnung, nicht die Taxonomie
- **0800 Nahrungs-/Genussmittel = Kat 2 oder Kat 3?** (entscheidet T01 Hipp +52%)
- 0905 ist ein Sammelcode (Krankenhaus + Pflege + Kita) — splitten wir nach Sub-Typ?
- 0904 Kaufhäuser/Einkaufszentren = Kat 3 bestätigt? (REWE-Anker 562 €)
- Kat-Zuordnung der reinen Industrie-Codes (0100–0700): pauschal Kat 3?
