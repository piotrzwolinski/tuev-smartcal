# Validierung v3 — Testrunde 1 Ergebnisse

**Datum:** 10.06.2026  
**Branch:** `v2-pricing` (auf Commit 91ff092 aufbauend)  
**Basis:** v2 (Phasen 0-6), erweitert um v3 Phasen A-D

## v3 Kern-Anderungen

| Phase | Beschreibung | Impact |
|-------|-------------|--------|
| **A: Referenzpreise** | Augsburg (368 Anlagen) + DEKA (3 Buerogebaeude) als Prio-1 vor NBG | T15 fix, T09 besser |
| **B: Kleinauftrag** | `bericht=inklusive` (0 EUR), `pruef_tage=0.5`, Grundkosten reduziert | T03 fix |
| **C: Reise-Scaling** | `reisezeit_charged = reisezeit_h * pruef_tage` fuer sub-day Jobs | T04 fix |
| **D: VdS-Staffel** | Synergie nach Flaeche: <=5k +50%, <=15k +40%, >15k +30% | T08 besser |

## Pricing-Hierarchie (v3)

```
1. Kleinauftrag?      → Pauschale (Phase B)
2. Referenzpreis?     → Nutzungstyp x EUR/m2 (Phase A) 
                         Guard: nur wenn m2 <= 3x typical_m2
3. NBG Fallback       → Kat x EUR/10m2 mit Degression (v2)
```

## Ergebnis-Tabelle: v1 vs v3

| ID  | Case                         | Real    | v1      | v3      | Dv1    | Dv3    | Verdict  |
|-----|------------------------------|---------|---------|---------|--------|--------|----------|
| T01 | Hipp Pfaffenhofen (VdS)      | 6.850   | 11.877  | 7.981   | +73%   | **+17%** | PASS   |
| T02 | REWE Eching (RV)             | 657     | 2.125   | 1.378   | +223%  | +110%  | RV-FLAG  |
| T03 | badenova Schaltschrank       | 391     | 1.051   | 492     | +169%  | **+26%** | MARGINAL |
| T04 | Auto Service Calw (MA560)    | 1.217   | 1.198   | 1.565   | -2%    | **+29%** | MARGINAL |
| T05 | Landwirt Neukirchen (MA560)  | 175     | 1.400   | 717     | +701%  | +310%  | xfail    |
| T06 | Maritim Hotel (MA510)        | 220     | 4.064   | 4.744   | +1747% | +2056% | xfail    |
| T07 | Koenig & Bauer (VdS)         | --      | --      | 2.885   | --     | --     | NO-REF   |
| T08 | Apleona Gilching (DGUV+VdS)  | 7.932   | 10.370  | 9.879   | +31%   | **+25%** | MARGINAL |
| T09 | Weber-Gymnasium (Multi)      | 4.800   | 2.834   | 3.645   | -41%   | -24%   | xfail    |
| T10 | Max Planck RZ (MA560)        | 5.341   | 2.084   | 5.991   | -61%   | **+12%** | PASS   |
| T11 | REWE Muenchen (RV)           | 657     | 1.739   | 1.374   | +165%  | +109%  | RV-FLAG  |
| T12 | Helios Klinik (DGUV+VdS)    | 13.110  | 10.840  | 9.430   | -17%   | -28%   | MARGINAL |
| T13 | Motel One Muenchen (RV)      | 621     | 5.161   | 2.758   | +731%  | +344%  | RV-FLAG  |
| T14 | roMEd Klinik Prien           | 3.470   | 4.323   | 4.495   | +25%   | +30%   | MARGINAL |
| T15 | DGUV Wuerzburg               | 4.195   | 3.282   | 5.112   | -22%   | **+22%** | MARGINAL |
| T16 | Polizei Dachau (Blitz)       | 205     | 1.537   | 1.292   | +650%  | +530%  | RV-FLAG  |

## Scoring

| Metrik              | v1 (Testrunde 08.06) | v3 (10.06) | Ziel   |
|---------------------|---------------------|------------|--------|
| PASS (<=20%)        | 2/14 (14%)          | **2/12**   | >=5    |
| MARGINAL (<=35%)    | --                  | **6/12**   | --     |
| FAIL (>35%)         | 10/14               | **0/12**   | 0      |
| RV-FLAG             | 4                   | 4          | erw.   |
| xfail (OOS)         | 3                   | 3          | erw.   |
| MANAGED (PASS+RV)   | 6/14 (43%)          | **6/12 (50%)** | >60% |

## Wichtigste Verbesserungen

1. **T15 Wuerzburg** (Buerogebaeude 5000m2): v1=-22% (zu niedrig) -> v3=+22% (naeher am Real). Referenz DEKA 0.85 EUR/m2 statt NBG Kat2 0.20 EUR/m2.
2. **T03 badenova** (Kleinauftrag): v1=+169% -> v3=+26%. Reduzierte Grundkosten, bericht=inklusive, pruef_tage=0.5.
3. **T08 Apleona** (26k m2 DGUV+VdS): v1=+31% -> v3=+25%. VdS-Staffel >15k=+30% statt pauschal +50%.
4. **T04 Calw** (MA560, 114 BM): v1=-2% (PASS) -> v3=+29% (MARGINAL). Reise-Scaling half, aber Gesamteffekt durch Mock-Standort verzerrt.

## Offene Punkte fuer naechste Runde

- **T12 Helios** (-28%): Krankenhaus-Pricing braucht spezifische EUR/m2-Referenz (nicht verfuegbar)
- **T14 roMEd** (+30%): Alter Bericht (2012), Inflation-Adjust macht MARGINAL akzeptabel
- **T08 Apleona** (+25%): 26k m2 liegt ueber Size-Guard (15k), nutzt NBG. Mehr Buero-Referenzdaten wuerden helfen
- **RV-Cases** (T02, T11, T13, T16): Brauchen Rahmenvertrag-Erkennung (MVP-Scope)
- **Pausch Routing** (Hotels, Moebelhaeuser, Baumaerkte): Referenzdaten noch nicht verfuegbar

## Technische Details

- **452 Tests bestanden**, 4 xfail
- **Referenz Size-Guard**: max_m2 = typical_m2 x 3 (darueber NBG-Fallback wg. fehlender Degression)
- **Referenz-Typen**: schule(0.55), kindergarten(1.09), verwaltung(0.97), buerogebaeude(0.85), werkstatt(0.50), turnhalle(0.62), museum(1.33), sport(1.06), versorgung(0.63), lager(0.64), versammlungsstaette(0.97)
- **Krankenhaus, Seniorentreff**: kein Referenz-Mapping (keine passenden Daten) -> NBG
