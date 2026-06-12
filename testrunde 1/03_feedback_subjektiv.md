# Testrunde 1 — Subjektives / Verhaltens-Feedback

Feedback zu Gesprächsführung, UX, Methodik-Präferenzen — nicht direkt an Preisdaten messbar.

---

## S1. Chat fixiert sich auf Quadratmeter
**Alle Tester betroffen — meistgenannter Kritikpunkt**

| Tester | Situation | Zitat |
|--------|-----------|-------|
| Pausch | 48 UV, 4 Gebäude → fragt nach m² | "obwohl ich recht genaue Angaben gemacht habe... hat das System ständig auf den Quadratmetern herumgeritten" |
| Steinwidder | 545 BM ortsveränderlich → fragt nach m² | "die Quadratmeter haben wir natürlich nicht" |
| Pfilf | Motel One BM → fragt nach Zimmern | "der wollte von mir die ganze Zeit die Zimmeranzahl" |
| Pausch | 1 Schaltschrank → fragt nach Mitarbeitern | XLSX: "Anfrage nach Mitarbeiter sinnfrei, da exakt 1 Schaltschrank beschrieben" |
| Weiß | UV-Ortsfest + Maschinen → Schleife zu m² | "er wollte auch immer zu den Quadratmetern zurück, obwohl ich die Maschinen quasi hatte" |
| Pausch | BM-Anzahl gegeben → fragt nach m² | XLSX Anlage 4: "Warum Abfrage nach m² wenn Angabe der Betriebsmittel vorhanden?" |

**Methodisches Argument** (Pfilf): "wir kalkulieren zum Beispiel überhaupt gar nicht anhand von Quadratmeter — wir sind damit schon mehrfach auf die Nase gefallen. 1.700 m² kann 4 UV haben oder 40."

**Einordnung**: Teils berechtigt (m² ist NICHT der einzige/beste Treiber), teils Kommunikationsproblem (System könnte m² als optional statt Pflicht behandeln). Überlappung mit D4 (MA560 braucht kein m²) und D5 (1 Schaltschrank braucht kein m²).

---

## S2. MA560 abgelehnt statt berechnet
**Evidenz**: Weiß (Call) — 20 ortsveränderliche Geräte Kindergarten Waiblingen

**Zitat**: System: "Die Prüfung von ortsveränderlichen Geräten wird von anderen Fachleuten durchgeführt" → verwies auf "Elektrofachbetrieb"

**Einordnung**: Klarer Fehler im Routing. MA560 ist ein TÜV-SÜD-Produkt. System hat möglicherweise die geringe Geräteanzahl (20) als "nicht TÜV-relevant" interpretiert.

---

## S3. Irrelevante Empfehlungen
**Evidenz**:
- Pausch (8:00 Call): "RLT Hygieneinspektion Empfehlung bei ELT nehmen wir raus"
- DGUV-Kalkulation zeigt Blitzschutz-Empfehlung

**Einordnung**: Cross-Selling-Empfehlungen sind prinzipiell gut, aber müssen fachlich passen. RLT-Empfehlung bei einer reinen ELT-Prüfung irritiert.

---

## S4. Bedenken Überschneidung mit bestehendem Projekt
**Evidenz**: Pfilf (Call) — "Christoph Teilens Projektteam (überregionaler Vertrieb) hat Jahre an der Preisfindung bis auf Stromkreis-Ebene gearbeitet"

**Einordnung**: Berechtigte Sorge um Doppelarbeit. Pfeiffer bestätigte: Großkunden-Preislisten sind bereits integriert. Für PoC kein Blocker, aber für MVP muss Abstimmung mit Teilen-Team erfolgen.

---

## S5. Wunsch: Datei-Upload
**Evidenz**: Weiß (Call): "Kann ich auch Dateien reinladen?"

**Einordnung**: Feature-Request für MVP/Phase 2. Nicht im PoC-Scope.

---

## S6. Wunsch: Testzugang behalten
**Evidenz**: Weiß (Call): "Darf man den Testzugang weiter nutzen?"

**Einordnung**: Positives Signal — Tester sehen Nutzen trotz Ungenauigkeiten. → Zugang bleibt aktiv.

---

## S7. "Man muss sehr viele Daten wissen"
**Evidenz**: Pausch (Docx, T15): "Liegt 1000 drunter. Man muss sehr viele Daten wissen. Aus dem Internet bekommt man die nicht."

**Einordnung**: Fundamentale Herausforderung des PoC-Ansatzes. Aber genau dafür der Chat: fehlende Daten vom Kunden erfragen. Pausch sagt gleichzeitig: "der Ansatz dieses Tools ist ja auf Merkmale zurückzugreifen, die wir von einem Hausmeister bekommen... und trotzdem eine Preisgenauigkeit von 90-95 Prozent zu bekommen."

---

## S8. Praxisrelevanz-Anforderung
**Evidenz**: Weiß (Call): "es muss praxisrelevant sein. Ich kriege eine Anfrage vom Kunden, die nehme ich, werfe ihn da rein und dann soll etwas Gutes rauskommen."

**Einordnung**: Klare Erwartungshaltung: kein Forschungstool, sondern Produktiv-Tool. Für PoC akzeptabel wenn Demo-Cases stimmen.

---

## Positives Feedback (gesammelt)

| Tester | Was funktioniert hat | Zitat |
|--------|---------------------|-------|
| Weiß | Standard-Gebäude bis mittlere Größe | "bis eine gewisse Größe... da ist es immer relativ nah herangerutscht an den Preis" |
| Weiß | Multi-Site-Eingabe (12 Werke) | "sauber aufgelistet und dann zu jedem Werk einen sauberen Preis... Da war zwar eine Differenz, aber mit der habe ich leben können" |
| Pausch | Auto Service MA560 | "Da hat er tatsächlich mal den Nagel auf den Kopf getroffen" |
| Steinwidder | Reisekosten | "Die Reisekosten haben meiner Sicht auch gestimmt" |
| Veit | Wochenend-Tests | "recht positive Ergebnisse, Endsumme immer recht positiv" |
| Burgey | Gesamteindruck | "Es sind ja erst mal zwei Monate und dafür funktioniert es echt schon ganz passabel" |
| Pausch | Grundsätzliche Machbarkeit | "Zeigt mir, dass es funktionieren kann. Ich glaube aber, dass den Weg müssen wir auf jeden Fall noch nachschärfen." |
