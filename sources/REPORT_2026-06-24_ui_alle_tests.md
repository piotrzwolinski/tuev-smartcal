# UI-Testlauf 24.06.2026 — alle 23 Fälle (live Fly v26)

Lauf: `scripts/test_ui_cases.py` (Chat-UI, echter Pfad). **MANAGED 10/16 (62%) · 9 PASS.**

| # | Real | UI | Δ | Status |
|---|---|---|---|---|
| T01 Hipp VdS | 6.850 | 10.416 | +52% | FAIL |
| T02 REWE Eching | 848 | 848 | +0% | **PASS** |
| T03 badenova | 391 | 590 | +51% | FAIL |
| T04 Auto Service MA560 | 1.217 | 1.283 | +5% | **PASS** |
| T05 Landwirt | 175 | 418 | — | xfail (Ref defekt) |
| T06 Maritim | 220 | 5.439 | — | xfail (Ref defekt) |
| T07 König&Bauer | — | 2.861 | — | NO-REF |
| T08 Apleona Kombi | 7.932 | 8.038 | +1% | **PASS** |
| T09 Weber-Gym Multi | 4.800 | 3.730 | — | xfail (Multi) |
| T10 Max Planck MA560 | 5.341 | 5.378 | +1% | **PASS** |
| T11 REWE München | 848 | 848 | +0% | **PASS** |
| T12 Helios Kombi | 13.110 | 13.329 | +2% | **PASS** |
| T13 Motel One | 621 | 4.313 | — | xfail (Ref defekt) |
| T14 roMEd Klinik | 5.136* | 4.494 | −13% | **PASS** |
| T15 DGUV Würzburg | 4.195 | 4.707 | +12% | **PASS** |
| T16 Polizei Blitz | 205 | 1.295 | — | RV-FLAG |
| **#12** Landgericht 850 BM | 3.878 | 8.275 | +113% | FAIL (Preis-Regime) |
| **#13** Uni Erlangen 4 UV | 1.261 | 2.577 | +104% | FAIL (kein m²) |
| **#14** Aschaffenburg 41 UV | 4.842 | 7.812 | +61% | FAIL (kein m²) |
| **#15** Stuttgart 17 UV | 2.848 | 4.850 | +70% | FAIL (kein m²) |
| **#16** Immenstaad 1 UV | 677 | 549 | −19% | PASS (knapp) |
| #11 Autowerkstatt | fiktiv | Rückfrage | — | Bot fragt ✓ |
| #17 Fürstenzell VdS | — | Rückfrage | — | Bot fragt ✓ |

Demo-Set (validiert): T02·T04·T08·T10·T11·T12·T14·T15. Neue Fälle #12-16 = Phase 2.
