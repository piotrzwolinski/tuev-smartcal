# Session 17.–20.06.2026 — Tier-1, Daten, UI-Tests, Reports

**Branch:** `v2-pricing` · **Deploy:** Fly v26 (live) · **Status:** 8 PASS, MANAGED 9/11 (82 %).

## 1 · Tier-1 Pricing-Änderungen (umgesetzt, getestet, deployed)
| # | Commit | Was | Ergebnis |
|---|---|---|---|
| **A3** | `e57b6f7` | Einzelhandel-REWE-Staffel (562/848 €) als **RV-Flat all-in** | T02/T11 RV-FLAG → **+0 % PASS** |
| **A0** | `15707d1` | VdS-Kat: Kita separat · 0800-Produktion auf **eine Konstante** `KAT_PRODUKTION_0800` | Hipp-Flip = 1 Zeile |
| **D-K7** | `626c0f7` | Kat-7-Rate **5,42 → 8,00** (Monotonie-Bug; Graph==Konstante) + Invariante | T12 −35 % → **+17 % PASS**; 2 rote Tests grün |
| **A5** | `311ce83` | Hotel → **Motel-One-Zimmer-Staffel** statt NBG-m² | T13 Prüf 5.161 → 3.160 € |
| **V1** | `8c91627` | VdS-Hüllkurven-Validierung gegen reale MA505-Verteilung | Modell im Korridor bestätigt |
| **V3** | `f785561` | Inflation 2024/25 **8,3/5,5 % → 2,5/1,0 %** (Anker 641,23→657,26 €) | latent (Ref-Jahre 2024/25) |

Basis: Engine-Konsolidierung (Montag) + **S. Pausch-Antworten 17.06** lösten die Blocker.

## 2 · Neue reale Daten (Surówka)
- **S. Pausch-Antworten 17.06** (`emails/2026-06-17_pausch_antworten_rueckfragen.md`): REWE 848 €, Kombi=Verkaufsthema, Kita/0800/0904, Test 5/6 fehlerhaft, Industrie=Preisliste.
- **Helios-Angebot** (M. Pfeifer): T12 real = **54 h × 239 €/h Aufwand** (kein m²-Preis) → begründet Aufwand-Modell.
- **Motel-One-Liste 2025**: Hotel = Zimmer-Staffel → A5.
- **MA505-Export** (M. Burgey 18.06): **5.995 reale VdS-Ist-Umsätze**, Median 1.190 €. RV-Flat bestätigt (657,26 € = T02/T11-Real, 80×). **507+560 folgen.** → `data/2026-06-18_ma505_kaufm_analyse.md`.
- **Kliniken Schmieder** (M. Pfeifer 18.06): 6 Standorte, 6 VdS-Klinik-Anker (655–5.880 €/Campus), `data/schmieder_full.csv` (90 Pos., gegen PDF-Summen verifiziert).

## 3 · UI-Tests = kanonisch (statt Skript)
- Alle 16 Fälle am 19.06. **live im Chat-UI** getestet (echter Pfad: Haiku-Extraktion + Geocoding + Engine).
- **Harness** `backend/scripts/test_ui_cases.py` (`7390ae9`, Playwright headless) ersetzt `test_testrunde1_all.py` als kanonische Validierung. CLAUDE.md §3 aktualisiert. pytest-Unit-Guards bleiben separat.
- **Befund T03 badenova** (keine Regression): Skript-Fixture hatte falsche Koordinate (48.16 ≈ 22 km zu Freiburg); real Lahr 48.34 ≈ **49 km** → UI +51 % ist ehrlicher als Skript +26 %. Strukturthema = Kleinstauftrag-Reise (Reise > Prüf). T08: Ergebnis nutzungstyp-sensitiv („Büro" +1 % vs „Industrie" +38 %).
- Voller UI-Lauf: 8 PASS · 2 FAIL (T01 wartet S. Pausch, T03) · 1 RV · 1 NO-REF · 4 xfail.

## 4 · Reports (für AL-Tagung / Status-Call)
- **`sources/reports/2026-06-19_status_komplett.html`** — kanonischer Report: Übersicht (UI-Zahlen, grüne Gewinner-Zeilen) + Diese-Woche + Neue-Daten + Offen + Detail je Testfall (4. KPI-Box „Fr 19.06 live UI" + „Seit Montag"). Namen mit Initialen (S. Pausch usw.). Generator: `sources/reports/build_status_detail.py`.

## 5 · Offen / nächste Schritte
- **Hipp Kat 2/3** — Entscheidung S. Pausch (Fr 20.06) → 1-Zeilen-Flip `KAT_PRODUKTION_0800`. Letzter unmanaged FAIL.
- **EQ-Auflösung** (MA505 + Schmieder, S. Pausch) → Krankenhaus-/VdS-Kurve real kalibrieren.
- **507 + 560 Exporte** (Fr/Mo) → gleiche Validierung.
- **T03 Kleinstauftrag-Reise** (Bündelung/Geocoding) · **T08 Nutzungstyp-Extraktion robuster**.
- **Aufwand-Modell** (Helios) · **UI-Politur Demo-Fälle** (Piotr).

## Verifikation
pytest 547 passed / 5 failed (pre-existing: API-401, physio-graph) / 4 xfailed. UI-Lauf MANAGED 9/11.
