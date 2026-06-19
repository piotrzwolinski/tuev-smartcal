# MA505 (VdS 2871) — Kaufmännischer Export: Struktur, Befunde, Nutzung

**Quelle:** `files/2026-06-18_505-WP_bereinigt_final_v3.xlsx` (Burgey/Pausch 18.06).
**Bedeutung:** Erster **reale-Preise-Datensatz für VdS** überhaupt (bisher hatten wir 0 echte VdS-Preise zur Kalibrierung). Validiert direkt die RV-Flat-Hypothese (A3) und gibt eine Preis-Hüllkurve für `vds_pruefkosten`.

## 1 · Struktur
- **5.995 Zeilen**, 8 Spalten, Sheet1. **1 Auftrag = 1 Equipment (Anlage), 1:1.**
- Spalten: `Auftrag · Verkaufsbeleg · Equipment(EQ#) · Eckstarttermin · Serviceprodukt(=505-WP) · Gesamterlöse Ist · Gesamtsumme (Ist) · Umsatz laut Auftragsbericht`.
- **2.371 Verkaufsbelege** (mehrere Aufträge je Beleg → Filialnetze/Rahmenverträge).
- Zeitraum **2016–2026** (10 Jahre).
- Maßgebliche Preisspalte: **`Umsatz laut Auftragsbericht`** (nonzero in allen 5.995).

## 2 · Preis-Verteilung (Umsatz je Anlage/Auftrag)
| Quantil | p10 | p25 | **Median** | p75 | p90 | p99 | max |
|---|---|---|---|---|---|---|---|
| € | 385 | 657 | **1.190** | 2.045 | 3.882 | 10.734 | 136.308 |

→ **Reale VdS-Anlage = ~1.190 € Median**, lange Schwerindustrie-Schwanz bis >100 k.

## 3 · Schlüssel-Befunde
1. **RV-Flat empirisch bestätigt (A3):** häufigste exakte Werte sind **657,26 € (80×, 21 Belege, 2025/26)**, **641,23 € (81×, 33 Belege, 2024)**, **1.165,00 € (32×)**. Wiederkehrende identische Per-Anlage-Preise = **standardisierte Listen-/Pauschalpreise** (Filialnetze). 657,26 € ist **exakt der T02/T11-„Real"-Wert** → unsere RV-Flat-Annahme war richtig.
2. **Reale Inflation ≈ +2,5 %/Jahr:** derselbe Listenpreis 641,23 € (2024) → 657,26 € (2025/26). → unsere **~4 %-Annahme ist evtl. leicht zu hoch**, sollte gegen diese Reihe nachjustiert werden.
3. **52 Filialnetze** (Verkaufsbeleg > 5 Anlagen), Median-Umsätze 165–1.172 € → kleine standardisierte RV-Anlagen (REWE-Muster).
4. **VdS-Modell-Validierung (Hüllkurven-Check, ohne Merkmals-Join):**
   | Profil | unser VdS-Prüf | reale Lage |
   |---|---|---|
   | Büro 500 m² Kat2 | 405 € | < p25 (657) — evtl. zu niedrig |
   | Büro 2.000 m² Kat2 | 870 € | < Median (1.190) |
   | Handel 2.500 m² Kat3 | 1.475 € | Median–p75 ✓ |
   | Industrie 8.000 m² Kat3 | 3.650 € | ≈ p90 (3.882) ✓ |
   | Industrie 20.000 m² Kat3 | 6.850 € | **= T01 Hipp real 6.850 ✓** |
   → Curve grob im richtigen Korridor; **kleine/mittlere VdS-Anlagen evtl. leicht unterbepreist**.

## 4 · Limitierung
Der Export enthält **keine Anlagenmerkmale** (m², Nutzung, Kategorie, Verteilungen) — nur EQ# + Preis + Datum. **Curve-Kalibrierung per Merkmal braucht den EQ-Join** zu den MA505-Prüfberichten (EQ# = Join-Key, wie beim ZF-Industrie-Set). MA505-Berichte liegen im Upload, sind aber noch nicht extrahiert/im Repo.

## 5 · Was wir damit tun können
| # | Aktion | Aufwand | Voraussetzung |
|---|---|---|---|
| V1 | **VdS-Hüllkurven-Validierung**: Golden-/Testfälle gegen reale Quantile (p25/Median/p75/p90) prüfen, Über-/Unterbepreisung sichtbar machen | klein | nichts (sofort) |
| V2 | **RV-Flat-Anker erweitern**: 657,26/641,23/1.165 als belegte Listen-Anker in die Referenz aufnehmen (analog REWE-Staffel) | klein | nichts |
| V3 | **Inflation nachjustieren** (~4 % → ~2,5 %) anhand 641→657-Reihe | klein | Cross-Check 507/560 |
| V4 | **VdS-Curve re-kalibrieren per EQ-Join** zu MA505-Berichten (Preis ↔ Nutzung/m²/Verteilungen) → echtes VdS-Ground-Truth-Set | groß | MA505-Berichte extrahieren |
| V5 | **Testfälle direkt validieren**: EQ# von T01 Hipp / T07 / T08-VdS im Export suchen → exakte Realpreise | klein | EQ# der Testfälle |
| V6 | **507 + 560 gleich behandeln** (kommen Fr/Mo) → DGUV-ortsfest + MA560 Realpreis-Sets | — | warten auf Export |

**Sofort sinnvoll: V1 + V2 + V3** (klein, datengetrieben, kein Merkmals-Join nötig). **V4** ist der große Hebel, sobald die MA505-Berichte extrahiert sind.
