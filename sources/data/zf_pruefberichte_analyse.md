---
quelle: Prüfberichte ZF.zip (58 PDF, 84 MB) — extrahiert nach files/zf_pruefberichte/
typ: ground_truth_pruefberichte
kunde: ZF Friedrichshafen AG
gewerk: MA505-WP (VdS 2871, Befundschein VdS 2229)
---

# ZF-Prüfberichte — Bestand & Analyse (To-Do #7, Ergänzung)

## Bestand
**58 PDF · 55× MA505-WP (VdS 2871) + 3 Preislisten · 12 Anlagen · 3 Standorte ·
Längsschnitt 2018–2026.** EQ-Nummern = exakt die der ZF-Preisliste
(`zf_industrie_referenz.md`) → **Berichte und Preise sind verknüpfbar (über EQ + Auftrags-Nr.).**

| Standort | Anlagen (EQ) | Berichte | Jahre |
|---|---|---|---|
| FN Friedrichshafen | 1243310, 1243952, 1244724, 1244773, 3337819 | 19 | 2021–2026 |
| PA Passau | 1522613, 1522631 | 9 | 2018–2024 |
| SW Schweinfurt | 1542953, 1542961, 1542967, 1542987, 3310412 | 27 | 2020–2025 |

(Kein Saarbrücken — deckt sich damit, dass das SB-PDF nur Druckbehälter enthielt.)

## Was steht im Bericht (Stichprobe 4 neueste Berichte, Preise bekannt)

Alle = standardisiertes **VdS-2229-Befundschein-Formular** (identische Struktur, gut maschinell lesbar).

| Werk | VdS-Preis (Liste) | **Prüfdauer** | Trafo kVA | Gefährdungskat. | Mängel | Seiten |
|---|---|---|---|---|---|---|
| Werk 3 Kressbronn (klein) | **2.293 €** | **4,0 Std** | ~3.060 | b | 24 | 9 |
| Werk 1 Friedrichshafen | 5.814 € | 26,0 Std | 32.000 | c | ~130 | 27 |
| Schweinfurt Nord Gebäude | 14.112 € | 95,5 Std | 35.000 | b | 50 | 7 |
| Passau Werk I (groß) | **18.557 €** | **80,0 Std** | 29.030 | c | 175 | 17 |

### Zuverlässig vorhandene Felder (100% Fill) — nutzbar als Kalibrierungs-Feature
- **Prüfungsdauer (Std., reine Prüfzeit)** — stärkster Preistreiber.
- **Gesamtleistung Versorgungstransformatoren (kVA)** — Anlagengrößen-Proxy.
- **VdS-Gefährdungskategorie (a–d)** — Risiko-/Komplexitätsindikator.
- **Mängelanzahl** (durchnummerierte Lfd.-Nr.) — Umfangs-Proxy.
- **Art des Betriebes** (hier 4× Metallverarbeitung) + **Auftrags-Nr.** (Join-Key zum Preis).

### NICHT vorhanden (wichtig!)
- ❌ **Kein Preis im Bericht** → Preis nur extern via Auftrags-Nr./SAP.
- ❌ **Keine Fläche / m²** → bestätigt: m² ist auch bei VdS-Industrie nicht der Treiber.
- ❌ **Keine summierten Stückzahlen** (UV/Stromkreise/Leuchten) — nur indirekt aus den
  namentlich genannten Stationen in der Mängelliste rekonstruierbar.
- ⚠️ RCD-% nur 3/4; "geschätzte Verbraucher ≤5.000" nur in alter Formularversion (2019);
  Branchennr. nur 1/4 → nicht zuverlässig.

## Korrelation Mengengerüst ↔ Preis
**Sehr deutlich — über Prüfdauer (+ kVA + Mängel + Kategorie), NICHT über eine Einzel-Stückzahl.**
- Prüfdauer: 4 Std → 2.293 € … 80–95 Std → 14.112/18.557 €. Impliziter Stundensatz grob
  130–190 €/Std (Großanlagen) — passt zum ZF-Listensatz **197 €/h**. Kleinaufträge effektiv
  höher (Mindestpauschale).
- Trafo-kVA trennt klein (~3.000) vs. groß (~29–35.000) klar; innerhalb „groß" differenziert
  Prüfdauer/Mängelzahl. Schweinfurt = Ausreißer (95,5 Std bei nur 50 Mängeln → viele verteilte
  Gebäudekomplexe = Wegezeiten treiben Std.).

---

## Wie wir das nutzen können (Diskussion)

### Sofort / kurzfristig
1. **Validierungs-Datensatz statt Trainings-Datensatz.** Da kein Preis und keine m²/Stückzahlen
   im PDF stehen, sind die Berichte **kein direktes Trainingsmaterial fürs m²-Modell**. Wert =
   (a) Beleg, dass das m²-Modell für Industrie strukturell falsch ist, (b) Quelle für die
   Aufwands-Features.
2. **Aufwands-/Stundenmodell für Industrie verankern.** Die Daten stützen einen zweiten
   Pricing-Pfad: **Preis ≈ Prüfdauer × 197 €/h** (+ Mindestpauschale für Kleinaufträge).
   Prüfdauer wiederum schätzbar aus kVA + Gefährdungskategorie + erwarteter Mängel-/Stationszahl.
   → ergänzt den bottom-up-Geräte-Pfad aus `zf_industrie_referenz.md` (beide Wege führen zum
   selben Anlagenbestand-Treiber, nicht zu m²).
3. **EQ↔Preis-Join aufbauen.** Auftrags-Nr. + EQ als Schlüssel; Preise kommen aus der
   ZF-Preisliste (haben wir) bzw. später SAP (To-Do #14). Damit entsteht ein echtes
   Ground-Truth-Set Industrie: Mengengerüst-Features → realer Preis.
4. **Längsschnitt = Inflationsbeleg.** Mehrjahres-Reihen pro Anlage (z.B. FN/EQ1243952 2021→2026)
   erlauben, die Preissteigerung (~4%/Jahr, im Code hinterlegt) empirisch zu prüfen.

### Mittelfristig / abzustimmen (Fr 20.06.)
5. **Feature-Extraktion per Batch** (Haiku, wie Blitzschutz/DGUV-Pipeline): aus den 55 PDFs
   automatisch Prüfdauer, kVA, Gefährdungskat., Mängelzahl, Auftrags-Nr. ziehen → strukturierte
   Tabelle. Standardisiertes VdS-2229-Formular macht das robust.
6. **Industrie als eigener Produktzweig?** (Pricing-Frage #2 im Haupt-Raport.) Diese Berichte
   sind das Argument dafür: Industrie-VdS ist aufwands-/anlagengetrieben, nicht m².

### Grenzen
- n=4 gesichtet (alle ZF, alle Metallverarbeitung) → für branchenübergreifende Kalibrierung
  nicht repräsentativ. Vor Generalisierung weitere Branchen (Rahmenvertrags-Recherche, To-Do #10).
- Stückzahlen UV/Stromkreise nur mit OCR/LLM aus Mängellisten rekonstruierbar — aufwändig,
  fehleranfällig.

> **Hinweis Speicherung:** Die 83 MB rohe PDFs liegen unter
> `sources/data/files/zf_pruefberichte/`, sind aber per `.gitignore` vom Commit ausgeschlossen
> (zu groß für Git). Versioniert wird nur dieser Markdown-Extrakt. Bei Bedarf re-extrahierbar
> aus `Prüfberichte ZF.zip`.
