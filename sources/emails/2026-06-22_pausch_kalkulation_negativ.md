# S. Pausch — „Kalkulationsbeispiel - negativ" (Supermarkt 840 m², #9)

**Von:** S. Pausch → Piotr (+ M. Pfeifer) · **22.06.2026 11:34**
**Mail:** „Hallo Piotr, kannst du dir das mal ansehen, hier ist grad die Kalkulation **sehr schlecht**:" + Screenshot.

## Eingabe (Chat)
„DGUV Prüfung, Supermarkt 840 m² Verkaufsfläche, in 73433" (= Übersicht-Fall #9, Aalen).

## Was der Screenshot zeigt — ZWEI Bugs gleichzeitig
**Bug 1 — Chat-Summary ≠ Breakdown-Tabelle (Widerspruch im selben Ergebnis):**
- Chat-Text: „Gesamtpreis (netto): **562,00 €** … Prüfkosten 562,00 € … Confidence 90 % — solide Kalkulation auf Basis der Verkaufsfläche."
- Rechte Tabelle: Prüfkosten **702,50 €** · Gesamtbetrag **702,50 €**.
→ Die kundenseitige Nachricht und die Kalkulations-Tabelle zeigen **unterschiedliche Summen** (562 vs 702,50).

**Bug 2 — Reifegrad RG_1 (×1,25) halluziniert:**
Quellennachweis: „Reifegrad RG_1: ×1,25 → 140,5 €". Der Nutzer hat **nichts zum Zustand gesagt**. 562 × 1,25 = 702,50 → Quelle der Tabellen-Summe.

**Root-Cause (verifiziert im Code):** Der Default ist korrekt `RG_3` (×1,0, `merkmale.py:117`). ABER: Haiku **extrahiert fälschlich `reifegrad=1`**, und es gibt **keinen Strip-Guard für Reifegrad** — für Fläche existiert `_strip_hallucinated_flaeche` (chat.py), für Reifegrad **nicht**. Also leakt die Halluzination durch. Gleiche Klasse wie phantom-m², aber **trivialer Fix**: Zwillings-Funktion `_strip_hallucinated_reifegrad` (Reifegrad entfernen, wenn Kunde nichts zu Zustand/Reifegrad gesagt hat → Default RG_3).

## Quellennachweis (rechts unten)
- Geschätzte Prüftage: 1,0 (Heuristik)
- Grundkosten-Override: 0
- **Referenzpreis (Augsburg/Gersthofen/DEKA): 562 €** (S. Pausch 10.06) ← A3-Einzelhandels-Staffel greift korrekt (840 m² ≤ 2000 → 562 €)
- **Reifegrad RG_1: ×1,25 → 140,5 €** ← der Bug
- Reise all-inclusive: 0 · Bericht inklusive: 0

## Einordnung
- **A3-Routing funktioniert** (Supermarkt → 562 € RV-Flat). Gut.
- **Negativ = (a) Reifegrad-Halluzination ×1,25 + (b) Summary/Tabelle-Mismatch.** Beides macht aus einem korrekten 562-€-Ergebnis ein falsches 702,50-€ mit widersprüchlicher Anzeige.
- Neuer Reparatur-Punkt **P4** (Reifegrad-Default + Anzeige-Konsistenz) → `PLAN_REPARATUR_2026-06-24.md`.
