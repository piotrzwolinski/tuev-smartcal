# M. Burgey/S. Pausch — Versand-Export 507 + 560 (reale Faktura, vollständig)

**Thread:** Piotr 10.06 (Anfrage Export 507/505/560 wie 438/419/570) → S. Pausch „brauche Markus" →
M. Burgey 17.06 (505 „Geburtstagsgeschenk") → **M. Burgey 19.06 15:18: 507 + 560 („fehlende Auswertungen")**.
**Anhänge (24.06 erhalten):** `507-WP_final.xlsx`, `560-WP_final.xlsx`, `505-WP_bereinigt_final_v3 (1).xlsx` (= Duplikat 18.06).

## M. Burgey 19.06 (wörtlich)
> „Anbei die fehlenden Auswertungen. Die **Fakturen stimmten bei meinen Stichproben mit den Werten in der Excel überein. Sollte also passen.**"

## Daten (Surówka: `data/files/versand_export_24_06/`)
| Datei | MA | Zeilen | Spalten |
|---|---|---|---|
| 507-WP_final.xlsx | DGUV ortsfest | **8.094** | Auftrag · Serviceauftrag · Material · **Equipment(EQ)** · Eckstart · **Isterlös** |
| 560-WP_final.xlsx | ortsveränderlich | **3.658** | (dito) |
| 505-WP_…v3 (1) | VdS 2871 | 5.995 | (= 18.06, Duplikat) |

## ⭐ EQ-Join: Testfälle gegen harte Faktura (Isterlös) — alle bestätigt
| Fall | EQ | Faktura | Übersicht „Markus" |
|---|---|---|---|
| #13 Uni Erlangen | 2065503 | 1.121 / **1.261** | 1.261,41 ✓ |
| #14 Aschaffenburg | 1484135 | **4.842** | 4.842,24 ✓ |
| #15 Stuttgart | 2427833 | **2.848** | 2.848,09 ✓ |
| #16 Immenstaad | 2490109 | **677** | 677,26 ✓ |
| #12 Landgericht | 2229803 (560) | **3.878** | 3.877,80 ✓ |
→ „letzte Abrechnung" = realer Faktura-Isterlös. **Harter Ground-Truth.**

## Verteilungen (Isterlös > 0)
- **507/DGUV:** n=6.928 · min 7 · p25 295 · **median 587** · p75 1.294 · p90 2.904 · max 53.214 €
- **560/ortsv.:** n=3.155 · min 6 · p25 160 · **median 389** · p75 906 · p90 2.280 · max 50.054 €

## Bedeutung
**Vollständiges reales Kalibrier-Set für DGUV (507) + ortsveränderlich (560)**, joinbar per EQ. 507-Median 587 € (klein!) bestätigt: unser m²-Modell überschätzt den Normalfall. Mit EQ→Merkmale (Prüfberichte) wird daraus echtes Preis↔Merkmale-Training für den per-UV/Aufwand-Pfad. → `PLAN_REPARATUR_2026-06-24.md` §6.
