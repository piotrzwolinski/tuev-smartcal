# Blitzschutz Kalkulator — Originalspezifikation von Stefan Veit

**Quelle**: E-Mail von Stefan Veit (IS-EG1-AUG/SV), datiert 14.08.2025
**Kontext**: "vielen Dank für den sehr kurzweiligen Abstimmungstermin heute Vormittag. Wie vereinbart findest du in der Anlage das Leistungs- und Preisverzeichnis als Kalkulationsgrundlage für das Tool."

---

## Der zu kalkulierende Preis setzt sich zusammen aus:

### 1. Reisekosten vom nächsten TÜV SÜD Standort

**Requirement**: Das Tool muss sich anhand der eingegebenen Objektadresse jeweils den nächst möglichen TÜV SÜD Standort suchen und dann die Reisekosten berechnen.

**Reisekosten-Formel**: lt. LPV angesetzt (1,10 €/km, Reisezeit gemäß Stundensatz 180€/h)

**⚠ WICHTIG**: "Bei mehrtägigen Prüfungen ist von maximalen Anfahrten auszugehen."
→ Interpretation: bei mehrtägiger Prüfung = NUR 1 Hin-/Rückfahrt, nicht pro Tag!

**Folgende 23 Standorte sind zu beachten**:

| Nr | Standort | Straße | PLZ | Ort |
|---|---|---|---|---|
| 1 | Augsburg | Oskar-von-Miller-Straße 17 | 86199 | Augsburg |
| 2 | Berlin | Wittestraße 30, Haus LM | 13509 | Berlin |
| 3 | Darmstadt | Rüdesheimer Straße 119 | 64285 | Darmstadt |
| 4 | Dresden | Drescherhäuser 5 D | 01159 | Dresden |
| 5 | Essen | Kruppstraße 82-100 | 45145 | Essen |
| 6 | Filderstadt | Gottlieb-Daimler-Straße 7 | 70794 | Filderstadt |
| 7 | Freiburg | Hermann-Mitsch-Straße 36 A | 79108 | Freiburg |
| 8 | Hamburg | Syltsterstraße 2 | 22525 | Hamburg |
| 9 | Hannover | Göttinger Landstraße 10 | 30419 | Hannover |
| 10 | Heilbronn | Heiner-Daimler-Straße 9 | 74076 | Heilbronn |
| 11 | Hof | Erfreudenstraße 75 | 95032 | Hof |
| 12 | Karlsruhe | Am Rüppurer Schloß 1 | 76199 | Karlsruhe |
| 13 | Leipzig | Weserstraße 2 | 04159 | Leipzig |
| 14 | Mannheim | Dudenstraße 28 | 68167 | Mannheim |
| 15 | München | Westendstraße 199 | 80686 | München |
| 16 | Nürnberg | Edisonstraße 15 | 90431 | Nürnberg |
| 17 | Ravensburg | Rudolfstraße 15 | 88214 | Ravensburg |
| 18 | Regensburg | Friedenstraße 6 | 93051 | Regensburg |
| 19 | Rostock | Krusensternweg 2 | 18069 | Rostock |
| 20 | St. Ingbert | Am Alten Forsthaus 1 | 66386 | St. Ingbert |
| 21 | Trostberg | Gabelsbergerstraße 5 | 83308 | Trostberg |
| 22 | Ulm | Berlinger Straße 17 | 89079 | Ulm |
| 23 | Würzburg | Petrinstraße 33 A | 97080 | Würzburg |

### 2. Grundkosten-Bestandteile

- **Pauschale** für Auftragsanlage, Verwaltung, Angebotsgebühr: **256 €**
- **Pauschale Ordnungsprüfung** von Dokumenten: nur bei **baurechtlichen** Prüfungen, nicht im aktuellen Beispiel
- **Energie- und Prüfmittelpauschale**: **49 € je Prüftag, je Sachverständiger**
- **Tagegeld** für die Sachverständigen:
  - 6 bis < 8 h Außendienst: **6,00 €**
  - 8 bis < 14 h Außendienst: **25,00 €**
  - 14 bis 24 h Außendienst: **30,00 €**

### 3. Prüfkosten (Aufwand für die Durchführung der Prüfung vor Ort)

- **Abhängig von den Merkmalen, siehe Preisliste** (LPV B04 §8.1)
- LPV B04 §8.1: **33 €/Messstelle** (äußerer Blitzschutz)
- \>10 Messstellen: **besondere Vereinbarung** (nicht weiter spezifiziert)

### 4. Kosten für die Berichterstellung

- Abhängig von der Art der Prüfung
- Für Blitzschutzanlagen bei **kleinen Anlagen**: **119 €**
  1. Standardbericht mit einheitlicher Vorlage (Umfang bis 10 Seiten): **380 €**
  2. Standardbericht mit komplexem oder besonderem Sachverhalt sowie umfangreichen Anlagebeschreibungen: **550 €**
  3. Individueller Begutachtungsbericht außerhalb der Standardvorlagen: **n.V.**

---

## Vergleich mit unserer Implementierung

### ✓ Korrekt implementiert:
- Alle 4 Kostenblöcke (Reise + Grund + Prüf + Bericht)
- Alle Grundkosten-Werte (256€, 49€, Tagegeld 6/25/30€)
- Berichtskosten (119/380/550€)
- 33€/Messstelle
- Ordnungsprüfung nur bei baurechtlich

### ⚠ Zu korrigieren:
1. **23 Standort-Adressen** — wir hatten Stadt-Mittelpunkte, jetzt haben wir exakte Straßen → geocoden!
2. **Heilbronn** fehlt in unserer Liste (23. Standort)
3. **Hof** fehlt in unserer Liste (24. Standort)
4. **Mehrtägige Reisekosten** = NUR 1 Anfahrt (aktuell rechnen wir: km × 2 immer, aber das ist korrekt für 1 Anfahrt hin+zurück)
5. **Darmstadt** fehlt in unserer Liste

### ❌ Offen:
- Prüfkosten "abhängig von Merkmalen, siehe Preisliste" — welche Merkmale genau? → LPV B04 §8 ist unser Referenz
- Berichtstyp-Zuordnung (wann klein/standard/komplex?) → unsere Heuristik (≤10 MS / 11-40 / >40) nicht von Veit bestätigt
- Prüftage-Schätzung → nicht spezifiziert
