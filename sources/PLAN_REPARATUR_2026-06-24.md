# Reparaturplan — Testrunde 24.06 (phantom-m² + Folgeprobleme)

> Stand 24.06.2026. Auslöser: S. Pauschs 7 neue Fälle (#11–17) + EQ-Prüfberichte (19.06).
> 4/5 messbare neue Fälle FAIL (+60…+113 %). UI == alte Engine → keine Tier-1-Regression,
> sondern **strukturelle Modell-Lücken**, die neue Gebäudetypen (Uni/Schule ohne m², Bulk-MA560) freilegen.

## 1 · Drei distinkte Probleme
| # | Problem | Fälle | Mechanismus |
|---|---|---|---|
| **P1** | **Phantom-m²** | #13/14/15 (+104/+61/+70 %) | MA507 ohne m² → System schätzt `m² = UV×400` (`UV_TO_M2_FACTOR`, chat.py) → Fläche×Kat überschätzt ~2×. Im UI sichtbar: „Geschätzte Größe 16.400 m²" = 41 UV × 400. |
| **P2** | **MA560-Bulk** | #12 Landgericht (+113 %) | flat 9,50 €/BM, keine Degression. 850 BM × 9,50 = 8.275; real 4,56 €/BM (RV/Volumen?). |
| **P3** | **Kleinauftrag-Floor** | #16 Immenstaad (−19 %) | 270 € flat zu niedrig für Produktion+Labor (real 677 €). |
| **P4** | **Reifegrad-Halluzination + Anzeige-Mismatch** | #9 Supermarkt (S. Pausch 22.06 „negativ") | Haiku extrahiert `reifegrad=1` (×1,25) obwohl Kunde nichts zum Zustand sagt; **kein Strip-Guard** (Fläche hat einen, Reifegrad nicht) → 562 → 702,50 €. Zusätzlich: Chat-Summary (562) ≠ Tabelle (702,50). |

## 2 · Schlüssel-Evidenz (was den Fix-Weg bestimmt)
**(a) Per-UV-Fit trifft Realität auf ±11 %** (Schule/Uni, all-in):
```
Preis ≈ 1.019 € + 95 €/UV
#13 Uni (4 UV)  Real 1.261 → 1.399 (+11%)  [m²-Modell: +104%]
#15 Schule(17)  Real 2.848 → 2.635 (−7%)   [m²-Modell: +70%]
#14 Gym  (41)   Real 4.842 → 4.917 (+2%)    [m²-Modell: +61%]
```
→ Diese Gebäude sind durch **UV** gut beschrieben, nicht durch Fläche. m²-Pfad = falsches Modell für sie.

**(b) EQ-Join (Schmieder-Befundscheine, 19.06): reale Prüfberichte erfassen KEIN m².**
Konstanz EQ1268813 (2.151 €): **Prüfdauer 4,0 Std · Gefährdungskat (c) · 800 kVA · Nutzung Krankenhaus** — Fläche nicht erfasst. kVA korreliert mit Preis (150→655 € · 800→2.151 € · 2.260→5.880 €).
→ Härtester Beleg für „weg von m²": die Prüfrealität läuft über **Aufwand (Stunden) + Komplexität (Gef.-Kat/kVA/UV)**, nicht m².

## 3 · Fix-Optionen
| | Option | Was | Aufwand | Bewertung |
|---|---|---|---|---|
| A | UV→m²-Faktor senken (400→~200) | Proxy-Proxy | ~30 min | Pflaster, typ-blind |
| D | Cap/Discount auf *geschätzte* Fläche (×0,5–0,6) | nur wenn m² geschätzt | ~1 h | Pflaster, schneller Demo-Fix |
| C | MA507 **fragt** nach m² (wie MA560 nach BM) | kein stilles Erfinden | ~1 h | ehrlich, aber Friction + hilft nicht ohne m² |
| **B** ⭐ | **Per-UV/Merkmale-Pricing** wenn kein m² (base + €/UV per Typ) | umgeht Fläche×Kat | mittel | **strukturell, Fit ±11 %** |
| **Hybrid** | m² da → Fläche×Kat (REWE/Apleona/Würzburg ok); nur UV/Merkmale → Pfad B | zwei Pfade je Input | mittel | **Ziel-Architektur = Zwei-Stufen-Ansatz S. Pausch** |
| **(C-Aufwand)** | mittelfristig: **Stunden × Satz + Gef.-Kat/kVA** | echtes Modell wie Helios/Schmieder | groß | nach Tagung; EQ-Join liefert Daten |

### Nebenfixes
- **P2 MA560:** Staffel/Degression für hohe BM-Zahl. **Zuerst S. Pausch fragen: Landgericht = Rahmenvertrag-flat?** („all incl?").
- **P3 Kleinauftrag:** Floor Merkmale-abhängig (Produktion/Labor → höher).
- **P4 Reifegrad (QUICK-WIN):** `_strip_hallucinated_reifegrad` analog zu `_strip_hallucinated_flaeche` — Reifegrad entfernen wenn Kunde nichts zum Zustand sagt → Default RG_3. Bug-Catcher-Test (Supermarkt-Prompt → kein ×1,25). + Anzeige: Summary-Nachricht soll Engine-Total nutzen, nicht eigene Zahl. **~1 h, kein Strukturthema.**

## 4 · Empfohlene Reihenfolge
1. **EQ-Join vertiefen** (Daten liegen jetzt vor, S. Pausch 19.06): Prüfdauer/kVA/Gef.-Kat/UV aus den Befundscheinen extrahieren → €/UV bzw. €/Std per Typ kalibrieren (statt 3 Punkte).
2. **Hybrid/Option B** umsetzen: kein m² → per-UV-Pfad. Quick-Win für #13–15 (FAIL→PASS).
3. **P2/P3** Nebenfixes (nach Pausch-Klärung Landgericht).
4. **C-Aufwand-Modell** (Stunden×Satz + Komplexität) = strukturelles Ziel nach AL-Tagung — durch Helios + Schmieder + ZF dreifach belegt.

## 6 · Kalibrier-Daten jetzt VOLLSTÄNDIG (Versand-Export 24.06)
M. Burgey lieferte die realen Faktura-Exporte (`data/files/versand_export_24_06/`):
**507-WP (8.094 Zeilen, DGUV)**, **560-WP (3.658, ortsv.)**, 505 (Dup 18.06) — je `EQ + Isterlös`.
- **EQ-Join bestätigt alle 5 Testfälle** als harte Faktura (#13=1.261 · #14=4.842 · #15=2.848 · #16=677 · #12=3.878). Kein Schätz-Risiko mehr.
- Verteilung 507-Median **587 €**, 560-Median **389 €** (klein) → m²-Modell überschätzt Normalfall systematisch.
- **Umsetzung Kalibrierung:** (1) EQ → Merkmale aus Prüfberichten ziehen (7 neue PDFs + Schmieder + Batch der 10k MA507-PDFs), (2) Regression **Preis ↔ UV/Prüfdauer/Gef.-Kat** je Gebäudetyp, (3) per-UV/Aufwand-Pfad damit kalibrieren (statt 3-Punkte-Fit). → ersetzt Option-B-Heuristik durch datengetriebene Stützstellen.

## 5 · Offene Fragen an S. Pausch
- Landgericht Amberg (850 BM, „all incl?") — Rahmenvertrag-Volumenpreis oder Standard?
- Bei m²-losen Anlagen (Uni/Schule): soll Bot **schätzen** (transparent) oder **fragen**, wenn Kunde kein m² hat?
- Gefährdungskategorie (a–d) — als Komplexitäts-/Preistreiber statt/neben Installationskategorie?
