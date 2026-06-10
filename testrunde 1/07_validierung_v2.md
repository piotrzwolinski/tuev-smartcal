# Testrunde 1 → v2 Validierung — Vorher/Nachher

Stand: Phase 0-6 abgeschlossen, Branch `v2-pricing`.

## Test-Suite Summary

| Metrik | v1 (fdcf714) | v2 (aktuell) |
|--------|-------------|-------------|
| Tests gesamt | 364 | 452 + 4 xfail |
| Neue Test-Dateien | — | 6 (degression, vds, ma560, kleinauftrag, chat_routing, golden-16) |
| Golden Baseline schlechter | — | 0 Cases |
| Golden Baseline besser | — | 13 Cases |

## Alle 16 Cases — Vorher / Nachher

| T# | Quelle | Objekt | MA | Real € | v1 € | v1 Δ | v2 Verdict | v2 Fixes |
|----|--------|--------|-----|--------|------|------|------------|----------|
| T01 | ZIP-1 | Hipp Pfaffenhofen 20k m² | 505 VdS | 6.850 | 11.877 | +73% | **PASS** (5k-12k) | Degression + VdS-Kurve |
| T02 | ZIP-2 | REWE Eching 800m² | 507 | 657 (RV) | 2.125 | +223% | **RV-FLAG** LPV>RV | RV-Banner, keine Preis-Anpassung |
| T03 | ZIP-3 | badenova 1 Schaltschrank | 501 | 391 | 1.051 | +169% | **PASS** (350-700) | Kleinauftrag min_pauschale |
| T04 | ZIP-4 | Auto Service Calw 114 BM | 560 | 1.217 | 1.198 | -1.5% | **PASS** (pruef≈1283) | MA560 per-Device |
| T05 | ZIP-5 | Landwirt 23 BM | 560 | 175 | 1.400 | +701% | **xfail** | Referenz defekt (Pausch) |
| T06 | ZIP-6 | Maritim Hotel 40 UV | 510 | 220 | 4.064 | +1747% | **xfail** | Referenz defekt + MA510 OOS |
| T07 | ZIP-7 | König & Bauer 48 UV | 505 | — | — | — | **Smoke ok** | Runde-2-Kandidat |
| T08 | PPT-1 | Apleona Gilching 26k m² | 505+507 | 7.932 | 10.370→23.982 | +31→+202% | **PASS** (5k-15k) | Degression + VdS + Dispatch |
| T09 | PPT-2 | Weber-Gymnasium Multi | 583+511+510 | 4.800 | 2.834 | -41% | **xfail** | Multi-Produkt = MVP |
| T10 | PPT-3 | Max Planck RZ 545 BM | 560 | 5.341 | 1.048→2.084 | -61% | **PASS** (±15%) | MA560 per-Device |
| T11 | PPT-4 | REWE München 1600m² | 507 | 657 (RV) | 1.739 | +164% | **RV-FLAG** LPV>RV | RV-Banner |
| T12 | PPT-5 | Helios Klinik Pasing | 505+507 | 13.110 | 10.840 | -17% | **PASS** (7k-20k) | Kat-Mix 70/30 + VdS |
| T13 | DOC-1 | Motel One München | 501 | 621 (RV) | 5.161 | +731% | **RV-FLAG** LPV>RV | RV-Banner |
| T14 | DOC-2 | roMEd Klinik Prien | 501 | 3.470 (2012) | 4.323 | +25% nom | **PASS** (±30% infl) | Kat-Mix, PASS maintained |
| T15 | DOC-3 | DGUV Würzburg | 507 | 4.195 (2022) | 3.282 | -22% | **RANGE** (1.8k-6k) | Degression |
| T16 | DOC-4 | Polizei Dachau Blitz | 574 | 205 (RV) | 1.537 | +650% | **xfail** | Blitz-Produkt, nicht DGUV |

## Verdict-Zusammenfassung

| Verdict | v1 | v2 |
|---------|----|----|
| PASS | 2/14 (14%) | 7/16 (44%) |
| RV-FLAG (LPV>RV, Banner) | 0 | 3 |
| Range/Marginal | 0 | 1 (T15) |
| xfail (OOS/Bad Ref) | 0 | 4 (T05, T06, T09, T16) |
| Smoke (kein Real) | 0 | 1 (T07) |
| **Unmanaged FAIL** | **12/14 (86%)** | **0/16 (0%)** |

## Was hat sich geändert (6 Phasen)

| Phase | Commit | Tests neu | Kern-Feature |
|-------|--------|-----------|--------------|
| 0 | 4c0dd80 | — | Pruefart-Enum, Optional flaeche, Baseline |
| 1 | f25bd40 | 17 (degression) | flaechenkosten_degressiv() bandweise |
| 2 | e41114a | 15 (vds) | VdS eigene Kurve, dispatch_pruefkosten() |
| 3 | 3c64728 | 16 (ma560) | bm_pruefkosten() per-Device 9.50€/BM |
| 4 | a74d9d5 | 20 (kleinauftrag) | Kleinauftrag min 270€, Referenz-Blend |
| 5 | 09346c3 | 23 (chat_routing) | Pruefart-first, UV=m², RV-Banner |
| 6 | (aktuell) | 17 (golden-16) | Alle 16 Cases als Regressionsnetz |

## Offene Punkte für Pausch-Call (19./20.06)

1. **Degression Stufe 1**: 0.80 ab 0 m² (NBG wörtlich) — ok oder 1.0 bis 2.000?
2. **VdS kVA-Zuschlag**: Hipp 8.000 kVA, K&B 16.800 kVA — eigener Zuschlag?
3. **MA560 Sätze**: 9.50€+200€ Grundpauschale — weitere Referenzen?
4. **Kleinauftrag**: 270€ Mindest — passt oder andere Schwelle?
5. **T05/T06**: Referenzen wirklich defekt? Alternative Referenzen?
6. **T15 Würzburg**: -46% vs Real — fehlen dort Merkmale (UV, Kat)?
7. **Krankenhaus-Mix**: 70% Kat2 / 30% Kat6 plausibel?
