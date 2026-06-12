# Plan v3 — Piątek 13.06.2026

Branch: `v2-pricing` (kontynuujemy, ostatni commit: `91ff092` Phase 6)

## Kontekst

- **Call Pausch 10.06:** m² = LETZTER Backup, Gersthofen/Augsburg = Prio 1, Nutzungstyp→Preisliste routing
- **v2 wyniki:** 3 PASS, 4 FAIL (T03 +75%, T04 +39%, T08 +40%, T15 -45%), 4 RV, 3 xfail
- **Cel piątek:** 0 FAIL, 5-7 PASS, zeigen dass Pausch-Approach (Nutzung-first) verstanden
- **Kluczowa zmiana podejścia:** Gersthofen/Augsburg = Prio 1 source, NBG = Fallback

## v2 Baseline (exact numbers from test runner)

```
T01  Hipp VdS 20k m²      real=6850   v2=7981   Δ=+17%   PASS     breakdown: G=678 P=5467 R=1286 B=550
T02  REWE Eching RV        real=657    v2=1378   Δ=+110%  RV-FLAG  breakdown: G=330 P=448  R=220  B=380
T03  badenova Schaltschr.  real=391    v2=683    Δ=+75%   FAIL     breakdown: G=100 P=270  R=194  B=119
T04  Calw 114 BM           real=1217   v2=1687   Δ=+39%   FAIL     breakdown: G=0   P=1283 R=404  B=0
T05  Landwirt 23 BM        real=175    v2=872    Δ=+399%  xfail    breakdown: G=0   P=418  R=453  B=0
T06  Maritim Hotel MA510   real=220    v2=4744   Δ=+2056% xfail    breakdown: G=384 P=1994 R=1816 B=550
T07  König & Bauer VdS     real=—      v2=2885   —        NO-REF   breakdown: G=330 P=1866 R=139  B=550
T08  Apleona DGUV+VdS      real=7932   v2=11110  Δ=+40%   FAIL     breakdown: G=796 P=9226 R=538  B=550
T09  Weber-Gym Multi       real=4800   v2=2323   Δ=-52%   xfail    breakdown: G=384 P=1428 R=131  B=380
T10  Max Planck 545 BM     real=5341   v2=5991   Δ=+12%   PASS     breakdown: G=0   P=5378 R=613  B=0
T11  REWE München RV       real=657    v2=1374   Δ=+109%  RV-FLAG  breakdown: G=330 P=647  R=18   B=380
T12  Helios DGUV+VdS       real=13110  v2=10659  Δ=-19%   PASS     breakdown: G=639 P=9220 R=250  B=550
T13  Motel One RV          real=621    v2=2758   Δ=+344%  RV-FLAG  breakdown: G=404 P=1614 R=191  B=550
T14  roMEd Klinik          real=3470   v2=4495   Δ=+30%   MARGINAL breakdown: G=443 P=2692 R=811  B=550
T15  DGUV Würzburg         real=4195   v2=2290   Δ=-45%   FAIL     breakdown: G=384 P=1428 R=98   B=380
T16  Polizei Blitz RV      real=205    v2=1292   Δ=+530%  RV-FLAG  breakdown: G=330 P=390  R=192  B=380
```

## 5 Phasen — Implementierung

### Phase A: Gersthofen/Augsburg Referenzpreise als Prio-1-Quelle — 5h ⭐ CENTERPIECE

**Warum:** Stefan Pausch 10.06: "Gersthofen hat detaillierte Angaben zu Nettogrundflächen 
und tatsächlichen Einzelpreisen — deutlich genauer als die Nürnberger Liste."

**Was:**
1. **Gersthofen-Excel lesen** (`input-files/Pruefung Elektrische Anlagen_Stadt Gersthofen_Preise_2025-04-14.xlsm`)
   - Pro Gebäudetyp extrahieren: Name, m², Preis, €/m², UV-Anzahl
   - Gebäudetypen: Turnhalle, Küche, Kindertagesstätte, Technikzentrale, Verwaltung, etc.
   
2. **Augsburg-Excel lesen** (`input-files/05_Preislisten_Grosskunden/Augsburg_StV_VdS_UVV.xlsx`)
   - Öffentliche Gebäude: Rathaus, Verwaltung, etc. mit realen Preisen

3. **DEKA-Daten lesen** (`input-files/05_Preislisten_Grosskunden/DEKA_Pfeiffer_2026_06_01`)
   - Bürogebäude München: Equipment-Level Preise

4. **Referenzpreis-Lookup bauen** — neues Modul `products/dguv_v3/referenzpreise.py`:
   ```python
   # Aus Gersthofen/Augsburg/DEKA extrahierte Referenzen
   REFERENZ_PREISE = {
       "turnhalle": {"quelle": "Gersthofen", "eur_per_m2": X.XX, "typical_m2": 800},
       "kueche": {"quelle": "Gersthofen", "eur_per_m2": X.XX, "typical_m2": 200},
       "kindertagesstaette": {"quelle": "Gersthofen", "eur_per_m2": X.XX, "typical_m2": 500},
       "verwaltung": {"quelle": "Augsburg", "eur_per_m2": X.XX, "typical_m2": 2000},
       "buerogebaeude": {"quelle": "DEKA", "eur_per_m2": X.XX, "typical_m2": 5000},
       # ... weitere aus Excel-Analyse
   }
   
   def lookup_referenzpreis(nutzung: str, flaeche_m2: float) -> float | None:
       """Prio 1: Referenzpreis aus Gersthofen/Augsburg/DEKA. None = Fallback auf NBG."""
       ...
   ```

5. **Engine-Integration:** `dispatch_pruefkosten()` prüft ZUERST Referenz-Lookup:
   ```python
   def dispatch_pruefkosten(m):
       ref = lookup_referenzpreis(m.nutzung, _flaeche(m))
       if ref is not None:
           return ref  # Gersthofen/Augsburg/DEKA
       # Fallback: NBG m²×Kat
       if is_kleinauftrag(m): return kleinauftrag_pruefkosten(m)
       return dguv_pruefkosten(m)
   ```

**Impact auf Cases:**
- T15 Würzburg (Büro 5k m²): DEKA/Augsburg Büro-Referenz → von -45% auf ±20%
- T08 Apleona (Büro 26k m²): DEKA Büro-Referenz → bessere Kalibrierung
- T01 Hipp (Industrie VdS): evtl. Gersthofen Industrie-Match
- T14 roMEd (Krankenhaus): DEKA Klinik-Referenz

**Dateien:**
- NEU: `products/dguv_v3/referenzpreise.py` — Referenz-Lookup Modul
- EDIT: `products/dguv_v3/pricing_rules.py` — `dispatch_pruefkosten()` mit Referenz-Prio
- EDIT: `products/dguv_v3/__init__.py` — ggf. pruefkosten() mit Referenz-Flag

**Tests:**
```python
class TestReferenzpreise:
    def test_lookup_buero_found(self):
        """Bürogebäude hat DEKA-Referenz."""
        ref = lookup_referenzpreis("buerogebaeude", 5000)
        assert ref is not None
        assert ref > 0

    def test_lookup_unknown_returns_none(self):
        """Unbekannte Nutzung → None → Fallback auf NBG."""
        ref = lookup_referenzpreis("atomkraftwerk", 5000)
        assert ref is None

    def test_referenz_vor_nbg(self):
        """Referenz-Preis wird VOR NBG verwendet."""
        m = DGUVMerkmale(nutzung="buerogebaeude", gesamtflaeche_m2=5000, ...)
        pruef_ref = dispatch_pruefkosten(m)  # mit Referenz
        # Sollte anders sein als pure NBG-Berechnung
        pruef_nbg = dguv_pruefkosten(m)
        assert pruef_ref != pruef_nbg

    def test_T15_wuerzburg_mit_referenz(self):
        """T15: 5000m² Büro mit DEKA/Augsburg-Referenz → ±25% von real 4195€."""
        angebot = engine.calculate(gewerk, merkmale_T15)
        assert 3000 < angebot.total < 5500

    def test_fallback_auf_nbg(self):
        """Nutzung ohne Referenz → NBG-Berechnung wie bisher."""
        m = DGUVMerkmale(nutzung="sonstige", gesamtflaeche_m2=3000, ...)
        pruef = dispatch_pruefkosten(m)
        assert pruef == dguv_pruefkosten(m)  # NBG fallback
```

### Phase B: Kleinauftrag-Fix (T03: F→B) — 2h

**Problem:** T03 badenova: 1 Schaltschrank, real=391€, v2=683€ (+75%).
Breakdown: G=100 + P=270 + R=194 + B=119 = 683€.
- Bericht=119€ für 1 Schaltschrank ist zu viel
- Reise=194€ für lokale Prüfung (5km, Freiburg) für 0.5 PT ist zu hoch

**Fix:**
1. `Bericht = 0` für Kleinauftrag (inkludiert in Pauschale)
2. `Prüftage = 0.5` für Kleinauftrag (fest, nicht aus Fläche berechnet)

**Ziel:** 683 - 119 (Bericht) - ~100 (Reise-Reduktion) ≈ 464€ → +19% → PASS

**Dateien:**
- `products/dguv_v3/__init__.py` — `bericht_typ_override()` returns "inklusive" for Kleinauftrag
- `products/dguv_v3/pricing_rules.py` — `dguv_estimate_pruef_tage()` returns 0.5 for Kleinauftrag
- `engine/gewerk.py` — check if `choose_bericht_typ` "inklusive" → bericht=0

**Tests:**
```python
def test_kleinauftrag_bericht_inklusive():
    """Kleinauftrag: Bericht inkludiert in Pauschale → bericht=0."""
    m = DGUVMerkmale(nutzung="sonstige", anzahl_verteilungen_nshv=1, adresse_plz="77933", adresse_lat=48.16, adresse_lon=7.85)
    assert is_kleinauftrag(m)
    assert dguv_choose_bericht_typ(m) == "inklusive"
    assert dguv_estimate_pruef_tage(m) == 0.5

def test_T03_badenova_total():
    """T03: 1 Schaltschrank → total ≤ 520€, real=391€."""
    angebot = engine.calculate(gewerk, merkmale_T03)
    assert angebot.breakdown.bericht == 0
    assert angebot.total < 520
    assert angebot.total > 300
```

### Phase C: MA560 Reise-Fix (T04: D→B) — 2h

**Problem:** T04 Calw: 114 BM, real=1217€, v2=1687€ (+39%).
Reise=404€ ist zu hoch für 1-Tages-Prüfung.

**Diagnose prüfen:** Wie berechnet `engine/pricing_engine.py` Reise?
- `dguv_estimate_pruef_tage(114 BM)` = max(0.5, 114/200) = 0.57 PT
- Aber Reise=404€ für 0.57 PT + 55km (Calw→Filderstadt) ist zu viel
- Vermutung: Reise hat Mindest-Overhead oder rechnet mit ganzen Tagen

**Fix:**
- MA560 ≤200 BM: max 1 Reisetag (nicht Mehrtages-Zuschlag)
- Prüfen ob Reise per Prüftag oder per Anfahrt berechnet wird
- Ggf. Reise-Berechnung für kurze Prüfungen anpassen

**Ziel:** 1687 - ~250 (Reise-Reduktion) ≈ 1430€ → +18% → PASS

**Dateien:**
- `engine/pricing_engine.py` — Reise-Berechnung analysieren + fixen
- `products/dguv_v3/pricing_rules.py` — ggf. Prüftage-Berechnung

**Tests:**
```python
def test_ma560_reise_eintaegig():
    """MA560 ≤200 BM = 1 Prüftag → 1 Anfahrt."""
    m = DGUVMerkmale(nutzung="industrie", pruefart="dguv_ortsv", anzahl_betriebsmittel=114, ...)
    assert dguv_estimate_pruef_tage(m) <= 1.0

def test_T04_calw_total():
    """T04: 114 BM → total ≤ 1500€, real=1217€."""
    angebot = engine.calculate(gewerk, merkmale_T04)
    assert angebot.breakdown.reise <= 250
    assert 1100 < angebot.total < 1500
```

### Phase D: VdS-Synergie Staffel (T08: D→C/B) — 1h

**Problem:** T08 Apleona: DGUV+VdS 26k m², real=7932€, v2=11110€ (+40%).
VdS × 1.5 ist zu viel für große Anlagen (mehr Overlap bei Großanlagen).

**Fix:** Staffel statt flat 50%:
```python
def _vds_synergie_faktor(flaeche_m2: float) -> float:
    """Bei großen Anlagen sinkt der Synergie-Zuschlag (mehr DGUV↔VdS Overlap)."""
    if flaeche_m2 <= 5000:
        return 0.50  # wie bisher
    if flaeche_m2 <= 15000:
        return 0.40
    return 0.30  # Großanlagen: nur +30%
```

**Ziel:** P = VdS(26k) × 1.3 ≈ 8000 → Total ≈ 9884€ → +25% → C

**Dateien:**
- `products/dguv_v3/pricing_rules.py` — `dguv_plus_vds_pruefkosten()` mit Staffel

**Tests:**
```python
def test_vds_synergie_staffel_klein():
    """≤5000 m²: Synergie = 1.50 (wie bisher)."""
    m = DGUVMerkmale(nutzung="buerogebaeude", pruefart="dguv_plus_vds", gesamtflaeche_m2=3000, ...)
    assert dguv_plus_vds_pruefkosten(m) == pytest.approx(vds_pruefkosten(m) * 1.5, rel=0.01)

def test_vds_synergie_staffel_gross():
    """>15000 m²: Synergie = 1.30 (Großanlage)."""
    m = DGUVMerkmale(nutzung="buerogebaeude", pruefart="dguv_plus_vds", gesamtflaeche_m2=26000, ...)
    assert dguv_plus_vds_pruefkosten(m) == pytest.approx(vds_pruefkosten(m) * 1.3, rel=0.01)

def test_T08_apleona_improved():
    """T08: DGUV+VdS 26k m² → total < 10500€ (real=7932)."""
    angebot = engine.calculate(gewerk, merkmale_T08)
    assert angebot.total < 10500
```

### Phase E: Erkenntnisse + Golden Tests + Demo — 2h

1. **1-Pager:** `testrunde 1/10_validierung_v3.md` — Vorher/Nachher alle 16 Cases
2. **Golden-Tests updaten:** `tests/test_testrunde1_golden.py` — Ranges anpassen
3. **Test-Runner updaten:** `scripts/test_testrunde1_all.py` — Scoring A/B/C/D/F
4. **Für Call:** 2-3 Cases live zeigen, Approach erklären (Nutzung→Referenz→m²-Fallback)

## Reihenfolge

| Prio | Phase | Stunden | Impact |
|------|-------|---------|--------|
| 1 | **A: Gersthofen/Augsburg/DEKA** | 5h | T15 fix, T08 besser, APPROACH correct |
| 2 | **B: Kleinauftrag** | 2h | T03 fix |
| 3 | **C: MA560 Reise** | 2h | T04 fix |
| 4 | **D: VdS-Synergie** | 1h | T08 besser |
| 5 | **E: Summary + Tests** | 2h | Freitag-Delivery |

**Phase A zuerst** — das ist was Stefan sehen will. Quick wins danach.

## Exit-Gate Freitag

| Metrik | v2 (jetzt) | v3 Target | Gate |
|--------|-----------|-----------|------|
| PASS (≤20%) | 3 | ≥5 | Pflicht |
| FAIL (>35%) | 4 (T03,T04,T08,T15) | 0 | Pflicht |
| F (>50%) | 2 (T03,T15) | 0 | Pflicht |
| Gersthofen-Referenz aktiv | nein | ja | Pflicht (Pausch-Feedback) |
| Alle Tests grün | 401+52 | 401+65+ | Pflicht |

## Quell-Dateien

- `input-files/Pruefung Elektrische Anlagen_Stadt Gersthofen_Preise_2025-04-14.xlsm` — Gersthofen Preisliste
- `input-files/03_Ausschreibungen/Gersthofen_DGUV_V3_2025.xlsm` — Gersthofen Ausschreibung (evtl. Duplikat)
- `input-files/05_Preislisten_Grosskunden/Augsburg_StV_VdS_UVV.xlsx` — Augsburg öffentl. Gebäude
- `input-files/05_Preislisten_Grosskunden/DEKA_Pfeiffer_2026_06_01` — DEKA Bürogebäude
- `input-files/059E-2025_Ausschreibungsunterlagen  2025-05-02 - LV DGUV V3 2025 - 2025 Wie.xlsm` — Audi LV

## Komenda do startu (po wyczyszczeniu kontekstu)

```
Przeczytaj 'testrunde 1/09_plan_v3_piątek.md' i memory session_2026_06_10_v3_plan.md.
Implementuj v3: Phase A (Gersthofen/Augsburg/DEKA Referenzpreise) → Phase B (Kleinauftrag) 
→ Phase C (MA560 Reise) → Phase D (VdS Synergie) → Phase E (Summary).
Branch v2-pricing, ostatni commit 91ff092.
Zacznij od Phase A: przeczytaj Gersthofen Excel i wyciągnij ceny per Gebäudetyp.
```
