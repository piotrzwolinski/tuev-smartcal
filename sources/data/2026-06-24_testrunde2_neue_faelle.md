# Testrunde 24.06 — neue Testfälle + Prüfberichte (EQ-Join verfügbar)

**Quelle:** `files/tuev_24_06/` (Drop 24.06): `Testkalkulationen_Übersicht (1).xlsx` (17 Anlagen)
+ **7 Prüfberichte-PDFs** (6× MA507-WP, 1× MA560-WP) mit EQ-Nummern, Datum 03.03.–03.06.2026.
**Bedeutung:** Erstmals neue Fälle **mit hinterlegtem Prüfbericht (EQ)** → echter EQ-Join (Preis ↔ Anlagenmerkmale) möglich.

## Die 5 neuen Fälle (#12–16, EQ-Prüfbericht + reale Abrechnung)
| # | MA | Objekt | PLZ | Angaben | EQ | SmartCal(alt) | **Real** | Anm. |
|---|---|---|---|---|---|---|---|---|
| 12 | 560 | Landgericht Amberg | 92224 | **850 Betriebsmittel** | 2229803 | 8.275 (+113 %) | **3.877,80** | „all incl?" |
| 13 | 507 | Uni Erlangen, 1 Gebäude | 91058 | **ca. 4 Unterverteilungen** (kein m²) | 2065503 | 2.576,81 (+104 %) | **1.261,41** | — |
| 14 | 507 | Aschaffenburg (Schule?) | 63739 | **41 UV**, 1 Küche, 1 Turnhalle (kein m²) | 1484135 | 7.811,86 (+61 %) | **4.842,24** | — |
| 15 | 507 | Grund-/Hauptschule Stuttgart | 70178 | **2 Gebäude, 17 UV** (kein m²) | 2427833 | 4.849,97 (+70 %) | **2.848,09** | — |
| 16 | 507 | Immenstaad, Produktion+Labor | 88090 | 1 Produktionshalle, 1 Labor, **1 UV** | 2490109 | 548,81 (−19 %) | **677,26** | „ggf. gut verkauft" |

> SmartCal(alt) = `Ergebnis`-Spalte = **alte (v1/vor-Konsolidierung) Engine** — durchweg überhöht (außer #16). Jetzt im **aktuellen UI** nachzutesten → `sources/ui_results.json` / Report.

## Schlüssel-Beobachtungen
1. **„Weg von m²" — ernst.** 4 der 5 MA507-Fälle sind über **Unterverteilungen + Gebäudemerkmale** beschrieben, **ohne m²**. Genau das, was S. Pausch/S. Veit wollen. Test: rechnet unser Modell sinnvoll ohne Fläche (über UV/Merkmale)?
2. **Reale Abrechnungen vorhanden** (nicht defekt wie T05/T06) → belastbares Ground-Truth-Set.
3. **EQ-Join jetzt machbar:** die 7 PDFs enthalten die Anlagenmerkmale (m²/Verteilungen/Prüfdauer) zu genau diesen EQ → Preis ↔ Merkmale verknüpfbar (wie beim ZF/MA505-Wunsch). 2 PDF-EQ (2848913, 3180914) sind **nicht** in der Übersicht-Liste — separat prüfen (Zusatz-Berichte?).
4. **Übersicht enthält auch fiktive/offene Zeilen** (#9–11 Aalen/Autowerkstatt „all incl", #17 Fürstenzell ohne Werte) + Tabs „Tests 15./22./23.06." (leer) — laufende Erweiterung.

## To-Do
- [ ] #12–16 im aktuellen UI testen (läuft) → Δ vs Real, Ursachen der Abweichung.
- [ ] EQ-Join: m²/UV/Prüfdauer aus den 7 PDFs extrahieren → gegen Real plotten.
- [ ] Prüfen: warum alte Engine durchweg +60–113 % (UV-Preis zu hoch? doppelte Fläche+UV? Reise?).
