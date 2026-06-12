# Testrunde 1 — Datenbasiertes Feedback

Feedback mit messbarer Evidenz: Preisvergleiche, Code-Bugs, technisch nachweisbare Fehler.

---

## D1. Flächenfaktor-Degression fehlt
**Auswirkung**: Alle Gebäude >2.000 m² betroffen
**Evidenz**:
- T01 Hipp 20.000 m²: 11.877 vs 6.850 (+73%)
- T08 Apleona 26.000 m²: 10.370 vs 7.932 (+31%)
- T12 Helios Klinik: 10.840 vs 13.110 (-17%)
- T09 Schule Multi: ~13.000 vs 4.800 (+171%)

**Root Cause**: Lineares Pricing `(m² / 10) × rate` ohne Degression. NBG Kalkulationshilfen zeigen klar sinkende €/m²-Sätze:
- DGUV: 2.000m²=0.80, 4.000=0.60, 6.000=0.50, 10.000=0.40, 25.000=0.30
- VdS: 2.000m²=0.90, 4.000=0.80, 6.000=0.70, 10.000=0.50, 25.000=0.35

**Betroffene Testfälle**: T01, T08, T09, T12

---

## D2. VdS-Stub gibt DGUV-Preis zurück
**Auswirkung**: Alle VdS-Kalkulationen falsch
**Evidenz**:
- Code `pricing_rules.py:388`: `vds_pruefkosten()` = `return dguv_pruefkosten(m)`
- `VDS_ID_PAUSCHALE = 208.00` deklariert (line 24) aber nirgends verwendet
- VdS hat eigenen Stundensatz (208€ vs DGUV LPV), eigene Degressionen

**Root Cause**: Stub-Funktion nie mit echter VdS-Logik gefüllt

**Betroffene Testfälle**: T01, T08, T12

---

## D3. VdS-Only zeigt DGUV+VdS doppelt
**Auswirkung**: Verwirrung + falsche Preise bei reinen VdS-Anfragen
**Evidenz**:
- Weiß (Call): "er hat mir Grundkosten, Prüfkosten, Reisekosten und VdS-Prüfung nochmal als Synergiepreis"
- Pausch (Call): "Prüfkosten von 6.000 und die VdS-Prüfung war nochmal mit 3.000 Euro beziffert"
- System berechnet IMMER erst DGUV-Basis, addiert VdS als Zuschlag

**Root Cause**: `dguv_plus_vds_pruefkosten()` hat keinen VdS-Only-Pfad

**Betroffene Testfälle**: T08, T12

---

## D4. MA560 per-Device-Pricing fehlt
**Auswirkung**: Ortsveränderliche Betriebsmittel systematisch falsch bepreist
**Evidenz**:
- T04 (114 BM): 1.198 vs 1.217 = **-1,5% PASS** (Zufall — m²-Ansatz trifft ungefähr)
- T05 (23 BM): 1.400 vs 175 = **+701%** (Grundkosten dominieren)
- T10 (545 BM): 2.084 vs 5.341 = **-63%** (m²-Logik skaliert nicht mit BM-Anzahl)

**Reales Pricing**: 545 BM × 9,80 €/Stück = 5.341€ (Max Planck Rechnung, PPTX Slide 15)

**Root Cause**: System nutzt Flächen-basierte DGUV-Logik statt per-Gerät-Rate

**Betroffene Testfälle**: T04, T05, T10

---

## D5. Kleine Aufträge systematisch überhöht
**Auswirkung**: Mini-Aufträge um Faktor 3-8× zu teuer
**Evidenz**:
- T03 (1 Schaltschrank): 1.051 vs 391 = **+169%**
- T05 (23 BM): 1.400 vs 175 = **+701%**
- T13 (Motel One): 5.161 vs 621 = **+731%** ("utopisch")
- T16 (Polizei Blitz): 1.537 vs 205 = **+649%** ("utopisch")

**Root Cause**: Grundkosten (256€ Auftragsverwaltung + Prüfmittel + Tagegeld = 572-671€) + Reisekosten übersteigen den eigentlichen Prüfumfang. System hat keinen Mindestpreis-Pfad.

**Betroffene Testfälle**: T03, T05, T13, T16

---

## D6. Referenzpreis wird ignoriert
**Auswirkung**: Altkunden-Preise fließen nicht in Kalkulation ein
**Evidenz**:
- Steinwidder (Call): Supermarkt DGUV, System=1.900€, Referenzpreis 545€ eingegeben, "ist aber trotzdem auf seinen Preis bestanden", Real=650€

**Root Cause**: Referenzpreis-Mechanismus existiert (`_apply_dguv_modifiers`), Gewichtung zu niedrig

**Betroffene Testfälle**: T02

---

## D7. Installationskategorien 7+8 fehlen
**Auswirkung**: Krankenhäuser und Ex-Bereiche falsch kategorisiert
**Evidenz**:
- Code `pricing_rules.py:29-36` hat nur Kat 1-6
- SBR-Tool definiert 8 Kategorien
- Kat 7 = 5.42€/10m² (AG2 Krankenhaus)
- Kat 8 = 7.68€/10m² (Ex-Bereich)

**Betroffene Testfälle**: T12, T14

---

## D8. PLZ → falscher Ort
**Auswirkung**: Falsche Standortanzeige + ggf. falsche NL-Zuordnung
**Evidenz**:
- Pausch XLSX Anlage 3: "PLZ passt nicht zu angezeigtem Ort, NL passt wiederum"
- Call: PLZ 77933 → zeigt "Bad Kissingen" (korrekt: Lahr/Hugsweier, Baden-Württemberg)

**Root Cause**: Geocoding-Fallback unzuverlässig

**Betroffene Testfälle**: T03

---

## D9. Reisekosten = 0€ bei nur PLZ
**Auswirkung**: Fehlende Reisekosten in der Kalkulation
**Evidenz**:
- Pausch (8:00 Call): Grundschule PLZ 93345 → Reisekosten 0€

**Root Cause**: Geocoding-Pipeline findet keine Koordinaten bei PLZ-only (vor Fix 5a0ea2b)

**Betroffene Testfälle**: Morgentests vor Testrunde

---

## D10. Inflationsbereinigung — Vorzeichen falsch
**Auswirkung**: Verwirrung: System zeigt Vergünstigung wo Verteuerung vorliegt
**Evidenz**:
- Call: "Abweichung von minus 6,88 Euro obwohl ich teurer geworden bin"

**Root Cause**: Vorzeichenlogik in Inflationsberechnung invertiert

---

## D11. Blitzschutz-Labels in DGUV-Output
**Auswirkung**: Fachlich falsche Bezeichnungen in DGUV-Kalkulation
**Evidenz**:
- Weiß (Call): "Messstellen und Staffelung" Label aus Blitzschutz erscheint bei DGUV

**Root Cause**: Template-Labels nicht produkt-spezifisch

---

## D12. Große DGUV massiv unterpreist (Einzelfall)
**Auswirkung**: System liegt bei großen komplexen Anlagen weit unter dem Angebotspreis
**Evidenz**:
- Weiß (Call): "große DGUV getestet, 14.000-15.000 ausgespuckt, wir haben 39.000 angeboten"

**Root Cause**: Fehlende Degression (D1) + fehlende höhere Kategorien (D7) + möglicherweise fehlende Zuschläge für komplexe Anlagen

---

## D13. Referenzpreise in Testdaten teils fehlerhaft
**Auswirkung**: Einige Testfälle nicht bewertbar
**Evidenz**:
- T05 (23 BM, 174,80€): Pausch markiert als "Abrechnung fehlerhaft"
- T06 (Maritim Hotel, 220€): Pausch markiert als "Abrechnung fehlerhaft" — 10-Seiten-Gutachten mit 46 Mängeln für 220€ unmöglich

**Implikation**: T05 und T06 sollten aus Pass-Rate-Berechnung ausgeschlossen oder mit korrekten Preisen neu bewertet werden
