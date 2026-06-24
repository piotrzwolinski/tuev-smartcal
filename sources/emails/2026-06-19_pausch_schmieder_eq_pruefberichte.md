# S. Pausch — Schmieder Prüfberichte nach EQs (EQ-Auflösung DGUV/VdS)

**Von:** S. Pausch → Piotr (+ M. Pfeifer) · **19.06.2026 07:22**
**Anhang:** `Kliniken Schmieder_2025-2027.zip` (+ Preisliste-PDF, Duplikat von 18.06)
**Kontext:** Antwort auf M. Pfeifer 18.06 („elektrische Anlagen unter einem Equipment — auf Basis EQ schauen was dahinter steckt"). **Löst die offene EQ-Auflösung.**

## Mail (wörtlich)
**M. Pfeifer 18.06:** „Preisliste einer Klinik mit mehreren Standorten. Der Posten elektrische Anlagen ist unter einem Equipment zusammengefasst. Kannst du hier auch wieder auf Basis der EQ Nummer schauen was sich dahinter verbirgt?"

**S. Pausch 19.06:** „anbei die **Prüfberichte nach EQs für die DGUV**. Die Preisliste wird für später auch interessant, **BMA, SiBe etc. ist hier mal schön identifizierbar**."

## ZIP-Inhalt: `schmieder_eq_2025-2027/extracted/`
4 EQ-Ordner (Schmieder VdS-Elektro-Anker), je mehrere Jahre (Wiederholungsprüfungen):
- **1268813** Konstanz (Preis 2.151 €) — 2017/2021/2025
- **1268824** Allensbach (5.880 €) — 2021/2025
- **1879930** Heidelberg (5.880 €) — 2017/2022 (+ IBN-EQ 2805355 MA501)
- **2122743** Stuttgart (655 €) — 2017/2022
(Gailingen 1267027 + Gerlingen 2122745 fehlen in diesem Batch.)
Reports = **MA505-WP** (VdS 2871 Befundschein).

## ⭐ EQ-Join-Befund (Konstanz 2025, EQ 1268813 = 2.151 €)
Der Befundschein steuert auf — und enthält **KEIN m²**:
| Feld | Wert |
|---|---|
| **Prüfungsdauer** | **4,0 Std** (reine Prüfzeit) |
| **Gefährdungskategorie** | **(c)** (VdS-Skala a–d) |
| **Trafo-Leistung** | 2× 400 kVA = 800 kVA |
| Nutzungsart | Sanatorien/Krankenhäuser/Pflege/Kita (VdS 0905) |
| Fläche m² | **— (nicht erfasst)** |

kVA korreliert grob mit Preis: Stuttgart ~150 kVA → 655 € · Konstanz 800 kVA → 2.151 € · Allensbach ~2.260 kVA → 5.880 €.

## Bedeutung
**Die realen Befundscheine erfassen Prüfdauer + Gefährdungskategorie + kVA + Nutzungsart — nicht m².** Das ist der härteste Beleg bisher für „weg von m²": unser m²-zentriertes Modell rechnet mit einer Größe, die in der Prüfrealität gar nicht vorkommt. Reale Treiber = **Aufwand (Stunden) + Komplexität (Gef.-Kat/kVA)**.

→ fließt in `sources/PLAN_REPARATUR_2026-06-24.md`.
