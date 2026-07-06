---
quelle: 4× Leistungen_Preise_ZF_*_2026.pdf + Anlage 1c_RV ZF_Bruttopreiseliste_2022-2025.xlsm
typ: industrie_referenzdaten
kunde: ZF Friedrichshafen AG (Industrie-Rahmenvertrag)
---

# ZF-Konglomerat — Industriereferenzdaten (To-Do #7)

Zwei Quelltypen:
- **4 PDFs (2026):** kundenfertige Angebote, Festpreise, DGUV V3 nur als **Gesamt-Anlagenpreis
  pro Werk** (keine Stückliste). Aufbau: Teil 1 Druckbehälter (irrelevant), Teil 2 Elektro
  (VdS 3602 + DGUV V3 ortsfest).
- **1 XLSM (RV-Ausschreibung 2022–2025):** das eigentliche **Mengengerüst** — Equipment
  Kategorie-für-Kategorie mit Stückzahlen UND Einheitspreisen. Nur Standorte 004/005/006
  (Saarbrücken, Lemförde, Aschau) sind voll bepreist.

## Teil A — PDF-Angebote 2026 (Netto, gültig bis 31.12.2026)

DGUV V3 ist **niemals einzeln** beauftragbar — nur Kombi mit VdS.

| Standort | Werk (EQ-Nr.) | VdS 2026 € | DGUV V3 2026 € |
|---|---|---|---|
| Passau | Werk I (1522613) | 18.557 | n.v. |
| Passau | Werk II (1522631) | 20.721 | n.v. |
| Schweinfurt | Aftermarket (1542987) | 6.007 | 2.950 |
| Schweinfurt | Nord Gebäude (1542953) | 14.112 | 4.528 |
| Schweinfurt | Nord Maschinen (1542967) | 17.341 | 8.670 |
| Schweinfurt | Süd Gebäude (3310412) | 9.996 | 4.780 |
| Schweinfurt | Süd Maschinen (1542961) | 22.849 | 8.760 |
| Friedrichshafen | Werk 1 +ABZ/Forum (1243952) | 5.814 | 6.244 |
| Friedrichshafen | Werk 2 (1244724) | 12.636 | 13.572 |
| Friedrichshafen | Werk 3 (1244773) | 2.293 | 2.368 |
| Friedrichshafen | Werk 4 (1243310) | 7.467 | 8.020 |
| Friedrichshafen | Werk 41 (3337819) | 1.144 | 1.229 |

**Saarbrücken-PDF** (abweichend, nur Druckbehälter + Konditionen):
- **Großkundenpreis Anlagenprüfung: 60,00 €/Prüfung**
- **Stundenverrechnungssatz: 197,00 €/h** (inkl. Reisezeit+Reisekosten)
- Zuschläge: So/Feiertag +100%, Samstag +50%; +2,00 € ANKA-Meldegebühr/Prüfung; kein Skonto.

**Regeln aus PDFs:**
1. **VdS = Pflicht-Anker, DGUV nur in Kombination.**
2. **DGUV-Preis ≈ 25% der VdS-Summe** (Hinweis: DGUV bezieht sich auf ~25% des Gebäudes,
   jährlich ein Viertel → 4-Jahres-Zyklus, stichprobenartig).
3. Preisbasis = Anlagenbestand Stand 08/2025. Keine m²-/Geräte-Granularität im Kundendoc.
4. Inflation: 2026 = 2025 × ~1,04.

## Teil B — XLSM Bruttopreisliste (Mengengerüst)

**Standortübersicht (virtueller Jahrespreis):** nur Saarbrücken (DGUV 97.132,89 €),
Lemförde (43.429,05 €), Aschau (43.970,40 €) sind bepreist. FRD/SWF/Passau = nur Mengen.

**Einheit (PME) durchgängig „Anlage / Gerät / Leuchte / Ableitung" — NIE m².**

**Equipment-Kategorien (Industrie-Merkmalsbaum):**
- 1 Versorgungsanlagen: MS-Trafos (kVA-Staffeln), MS-Schaltanlagen (kV × Felderzahl),
  Schutzgeräte, NS-Hauptverteilung, Batterie/Ersatzstrom, Diesel/Generator, USV
- 2 NS-Schalt/Installation: Blindleistungskompensation, aktive Filter, NS-Verteilung,
  **Stromkreise ohne RCD / mit RCD (mit/ohne Messung)**
- 3 Beleuchtung: Sicherheits-/Notbeleuchtung Einzel-/Zentralbatterie
- 4 Blitzschutz: BSK I/II, III/IV (Einheit = Ableitung)
- 5 Sätze/Zuschläge: Stundensätze, Hubsteiger €/Tag, Nacht +50%, So/Feiertag +100%, Anfahrt

**DGUV-V3-Einheitspreise (Sp.12, je Anlage sofern nicht anders):**

| Equipment | Saarbrücken | Lemförde | Aschau |
|---|---|---|---|
| MS-Trafo | 55,58 | 58,50 | 58,50 |
| MS-Schaltanlage (Feld) | 111,15 | 117,00 | 117,00 |
| Leistungsschalter | 48–68 | 68,00 | – |
| Blindleistungskomp. | 37,05 | 39,00 | 39,00 |
| **NS-Verteilung** | **55,58** | 58,50 | 58,50 |
| **Stromkreis mit RCD** | **11,02** | 11,60 | 11,60 |
| Stromkreis ohne RCD | – | 9,30 | 9,30 |
| Sicherheitsleuchte (Einzelbatt.) | 11,12/Leuchte | 11,70 | 11,70 |
| Sicherheitsbel.-Anlage GB/ZB | 1.060,20 | 1.116,00 | 1.116,00 |
| Blitzschutz (SV) | 18,40/Ableitung | 18,40 | (n.v.) |

(Lemförde/Aschau ~5% höher = Tarifindex.)

**Mengengerüst-Beispiel Friedrichshafen** (Industrie-Größenordnung): 178 MS-Trafos,
430 NS-Leistungsschalter, **2.895 NS-Verteiler, 30.000 Stromkreise o. RCD, 4.200 m. RCD**.
Gebäude ~580.000 m², aber "Ableitungen Blitzschutz nicht bestimmbar" → m² ist NICHT der Treiber.

## Ableitbare Industrie-Pricing-Regeln (DGUV V3)
1. DGUV-Preis = **bottom-up**: Σ (Geräteanzahl je Kategorie × Geräte-EP) / Prüfzyklus (meist 4 J).
2. Treiber = **Geräteinventar je Equipment-Kategorie**, nicht m².
3. **VdS Pflicht-Anker; DGUV ≈ 25% der VdS-Summe.**
4. Konstanten: Anlagenprüfung 60 €, **Stundensatz 197 €/h**, +2 € ANKA, Zuschläge wie oben, kein Skonto.
5. Geräte-EP-Anker: NS-Verteiler 55,58 / Stromkreis m. RCD 11,02 / MS-Trafo 55,58 /
   MS-Schaltfeld 111,15 / Sicherheitsleuchte 11,12 / Blitz-Ableitung 18,40.
