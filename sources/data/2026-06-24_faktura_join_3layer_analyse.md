# Faktura × Merkmale Join — 3-Schichten-Analyse der Preis-Varianz (24.06.2026)

**Quelle:** Session 24.06. Join `507-WP_final.xlsx` (Faktura/Isterlös je EQ) × `batch_MA507_results.json`
(10.096 extrahierte Merkmale, EQ aus Dateiname). **6.994 verknüpfte Datensätze.**
Reproduktion: Skript-Snippets in dieser Session / `scripts/calibrate_pricing.py`.

## Kernfrage
Lässt sich der real fakturierte Preis aus den technischen Merkmalen vorhersagen?
→ in-sample R² = **0,33** (Technik erklärt nur ⅓). Aber: **das R² ist durch Datenstruktur verzerrt.**

## Der scheinbare 46×-Spread — und seine Zerlegung
Gruppe „Bildungseinrichtung · 1 Prüftag · 0 HV · ≤1 UV · 0 Mängel" (technisch ~identisch, n=155):

| Sicht | n | min | median | max | Spread |
|---|---|---|---|---|---|
| ALLE (inkl. Bundle-Splits) | 155 | 62 € | 62 € | 2.892 € | **46×** |
| NUR standalone (1 EQ = 1 Auftrag) | 2 | 1.311 € | 2.102 € | 2.892 € | **2×** |

**→ Der 46×-Spread war zu ~95 % ein Bundling-Artefakt, NICHT Rabatt.**

### Beleg aus den Rechnungsdetails (Auftrag-Ebene)
- **Aschaffenburg 62,50 €** → Auftrag 3859744 = **212 EQ × 62,50 € = 13.062 €**.
  Das 62,50 € ist *kein Prüfpreis*, sondern 1/212-Split eines Rahmenvertrag-Sammelauftrags. (= Testfall #14)
- **Freiburg 1.311 €** → 1 EQ = 1 Auftrag, standalone. Bericht: **61 Messzeilen, 12 Räume** = real größerer Umfang.
- **Bayreuth 2.892 €** → 1 EQ = 1 Auftrag, standalone, voller Einzelpreis.

## Die drei Schichten der Preis-Varianz
Die ⅔ unerklärter Varianz (R²=0,33) sind ein **Mix aus drei Quellen** — zwei davon lösen wir selbst:

1. **Bundling / Auftragsstruktur** (dominant) — Sammelauftrag-Splits vs Einzelaufträge.
   → **selbst lösbar:** Spalte `Auftrag` ist im Export → Flag „standalone vs bundle", Bundle-Splits raus.
2. **Realer Prüfumfang** — Messzeilen/Räume, von der groben Signatur (nur UV/Prüftage/HV) übersehen.
   → **selbst lösbar:** `messungen_anzahl_zeilen`, `raeume_typen` sind in der Extraktion, nur ungenutzt.
3. **Vertrags-/Kundenrabatt** — Restspread auf echt vergleichbaren Standalone-Aufträgen.
   → **braucht eine Spalte von TÜV: `Kundennummer`/RV-ID** an die 6.000 Datensätze.

## Konsequenz / Korrektur früherer Aussage
- Früher (Session): „Preis nicht vorhersagbar = fehlende Variable (Rabatt)." → **zu stark vereinfacht.**
- Korrekt: **Bundling + Umfang sind der Großteil und intern lösbar**; nur die kleinste Restschicht
  (Kundenrabatt) braucht externe Daten. R²=0,33 ist durch Bundle-Splits gedrückt → nach Bereinigung höher.
- Das ist die **stärkere, ehrlichere Call-Linie:** „wir verstehen die Lücke zahlenmäßig und handeln den
  Großteil selbst; ein einziger Datenpunkt (Kundennummer) schließt den Rest."

## Was SmartCal rechnet vs. was in den Quellen steht (3 Datensätze, Join über EQ)
| | Prüfbericht | SmartCal | Faktura |
|---|---|---|---|
| Inhalt | technische Merkmale (Kostentreiber) | Listenpreis LPV | realer Isterlös |
| hat | gebäudetyp, PLZ, Prüftage, UV/HV, Messzeilen, Räume, NEA, Mängel | Grund+Reise+Prüf+Zuschläge | Isterlös €, Auftrag, EQ, Datum |
| hat NICHT | m², Preis, Kunde | — | Merkmale, Kunde/RV, Aufschlüsselung, Bundle-Flag |

SmartCal-Validierung an Stefan-Fällen: **#8 Grundschule** SmartCal ~2.494 € vs Faktura 2.380 € = **+5% ✅**
(standalone); **#13 Uni** ~2.580 € vs 1.261 € = **+104% ❌** (Bundle/RV-Verdacht — Auftrag+Kunde anfordern).

## Call-Narrativ (24.06)
> „SmartCal liefert die objektive Listenkalkulation aus dem Bericht — validiert (#8 +5%). Wo sie von der
> Faktura abweicht, haben wir es **zahlenmäßig zerlegt**: ~95% sind Bundling + Umfang, die wir selbst lösen.
> Eine Schicht bleibt — der Kundenrabatt — und dafür brauchen wir **eine Spalte: Kundennummer** an die 6.000
> Datensätze, die wir schon haben."

Bogen: **geliefert (F1/F2 live) → Lücke zahlenmäßig verstanden (3 Schichten, Beleg auf echten Aufträgen)
→ konkreter Ask (Kundennummer).**

## Offen / nächster Schritt
- **Harte Zahlen:** Volllauf über alle Gruppen — Spread mit/ohne Bundle + R² vor/nach Bereinigung
  (standalone-Filter + Umfang-Features), damit „~95%/2×" nicht auf n=2 beruht. ~3 min.
- Dann F2-Doc / Slide mit echten Vorher-Nachher-Zahlen finalisieren.
