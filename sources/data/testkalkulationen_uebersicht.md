---
quelle: Testkalkulationen_Übersicht.xlsx (Stefan Pausch, Stand 15.06.2026) + 20230413_EQ3295815_MA507-WP_.pdf
typ: testfaelle_ground_truth
---

# Testkalkulationen-Übersicht (Pausch) — extrahiert

Spalte N "Ergebnis" = **SmartCal-Berechnung** · Spalte O "letzte Abrechnung (lt. Markus)"
= **realer Ist-Preis TÜV** (Ground Truth). Farben: gelb=neu (Test 8), grün=Treffer,
rot=Problem.

## Alle 8 Testfälle

| Test | Material | Typ | PLZ | Gebäude/Nutzung | Mengengerüst | EQ-Nr | SmartCal (N) | Ist TÜV (O) | Abw. | Anmerkung |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 505 | VdS2871 | 85276 | Nahrungs-/Genussmittel | 8000 kVA, 45 UV, 20.000 m² | 1550815 | 11.877 | 6.850 | +73% 🔴 | "VdS kommt fast hin" |
| 2 | 507 | DGUV | 85386 | Rewe Markt | Kühltheke, ~800 m² | 2828424 | 2.125,28 | 657,26 | +223% | "Abrechnung ggf. zu gering" |
| 3 | 501 | el. Anlage | 77933 | 1 Schaltschrank | — | 3316380 | 1.051,06 | 391 | +169% | "Abfrage → zu hohe Preise?" |
| 4 | 560 | el. Betriebsmittel | 68167 | Auto Service | 114 Betriebsmittel, ~300 m² | 2597657 | 1.198,33 | 1.216,95 | **−1,5%** 🟢 | **"Passt!"** |
| 5 | 560 | el. Betriebsmittel | 93444 | Landwirt. Betrieb | 23 Betriebsmittel, 150 m² | 3578607 | 1.400 | 174,8 | +701% | "Abrechnung fehlerhaft" 🔴 |
| 6 | 510-wp | el. Anlage | 32105 | Maritim Hotel | 5 Konferenzr., Gastro, 40 UV, ~100 Zi. | 2909976 | 4.063,5 | 220 | +1747% | "Abrechnung fehlerhaft" 🔴 |
| 7 | 505 | VdS2871 | 1445 | Metallverarbeitung | 48 UV, 4 Geb., 80/20 Prod/Verw, 900 m² | 3218668 | 4.490 | 20.656 | −78% | (keine) |
| **8** | **507** | **DGUV** | **97076** | **Grundschule** | **25 Klassenr., 10 UV, Zustand 2, keine Wallbox/PV** | **3295815** | **2.928,74** | **2.380** | **+23%** 🟢 | **"Schaut gut aus!" (NEU)** |

**Lose Anmerkungen (Anlage-Sheets):**
- Test 3 (EQ 3316380): "PLZ passt nicht zu Ort, NL passt; Abfrage nach Mitarbeitern sinnfrei, da exakt 1 Schaltschrank."
- Test 4 (EQ 2597657): "Warum Abfrage nach m² wenn Angabe der Betriebsmittel vorhanden?"

**Kernbeobachtung:** Nur Test 4 (MA560, −1,5%) und Test 8 (MA507, +23%) grün = managed.
Test 5/6 rot wegen **defekter Ist-Abrechnung** (Referenz falsch, nicht unser Modell).

## Test 8 — Prüfbericht EQ3295815 (PDF) Detail
- TÜV SÜD IS, NL Würzburg. MA507-WP (Wiederholungsprüfung). Grundschule Würzburg-Lengfeld,
  Carl-Orff-Str. 6, 97076 Würzburg. Auftraggeber Stadt Würzburg.
- Prüfdatum 03.04. + 13.04.2023 (**2 Prüftage**), nächste Prüfung 04/2027 (4-Jahres-Intervall).
- Prüfumfang: Hauptverteilung + zahlreiche UV über mehrere Ebenen (HG UG/EG/1.OG/2.OG +
  Sporthalle + 2 Container + Garage). **~10 UV** (Excel-Annahme passt). Ortsveränderliche
  Betriebsmittel NICHT geprüft (auftragsgemäß ausgeschlossen).
- ~80 RCDs einzeln vermessen, 2 defekt. **46 Mängel** (Großteil Einstufung 1, 3× Einstufung 2,
  keine Einstufung 3). → "Zustand 2" der Excel passt.
- **Kein Preis im PDF.** Ist-Preis 2.380 € stammt aus Markus-Abrechnung. SmartCal 2.928,74 €
  (+23%, von Pausch grün gewertet).
