# Piotr → S. Pausch — Berichterstellung 119/550 € umgesetzt (Status)

**Ausgehende Mail** (Antwort auf S. Pauschs Berichterstellung-Regel vom 17.06 10:34,
siehe [2026-06-17_pausch_berichterstellung_119_550.md]). Stand: 24.06, nach Umsetzung + Live-Deploy.

---

Betreff: Berichterstellung 119/550 € — umgesetzt

Hallo Stefan,

danke für die Klarstellung — die Berichterstellung-Regel ist jetzt drin, genau wie beschrieben:

- DGUV / VdS / Blitz → immer der kleine Bericht mit 119 €.
- Komplexer Bericht (550 €) nur bei echtem Mehraufwand: Prüfung nach Baurecht, Elektrothermographie
  oder einer Kunden-Sonderanforderung an den Bericht (eigene Form / Sonderform der Übermittlung).
- Die alte Größen-Staffel (380 € „Standard") fällt damit weg.

Wie es greift:
- Die Baurecht-Kennung haben wir im Modell, die löst den komplexen Bericht automatisch aus.
- Elektrothermographie und Sonderanforderung sind als Schalter umgesetzt — die werden ja ohnehin beim
  Kunden abgefragt, also setzt der Angebotsersteller sie bewusst. Der 119-€-Baustein bleibt damit
  optional/transparent als eigene Position, wie von dir gewünscht („obliegt dem Angebotsersteller").

Auswirkung auf die Testfälle (Plausibilisierung):
Der Faktor bringt uns nicht höher, sondern in mehreren Fällen näher an die realen Werte — vorher haben
wir bei größeren Anlagen 380/550 € angesetzt, jetzt flache 119 €. Z.B. Hipp +17 → +10 %, Helios
+17 → +14 %, roMEd +19 → +8 %, Würzburg +11 → +5 %. RV-/Pauschal- und ortsveränderliche Fälle bleiben
unberührt (Bericht in der Pauschale enthalten). Keine Verschlechterung bei den bisher passenden Fällen.

Kurz zum Rest aus dem 17.06-Schriftwechsel — ist alles eingebaut:
- REWE-Liste als Referenz für alle Einzelhandelsprojekte (848 € für 2.001–5.000 m²)
- DGUV+VdS-Kombi als Verkaufslogik (× 1,20)
- VdS-Branchen: Kita separat, 0800 = Produktion / 0904 = Verkaufsstätten

Offen ist bei dir nur noch die Lebensmittel-Entscheidung (Hipp, Kat 2 vs. 3) — sobald die da ist, ist es
bei uns ein Ein-Zeilen-Flip.

Eine kurze Rückfrage hätte ich noch: bei OP/Intensiv hattest du „Faktor 2, Ansatz Anzahl Intensivplätze"
notiert — aktuell rechnen wir die Sonderfläche noch über m² × Kategorie (Rate angehoben). Sollen wir
wirklich auf Anzahl Intensivplätze umstellen, oder reicht die angehobene Flächen-Rate fürs PoC?

Viele Grüße
Piotr

---

## Live-Verifikation (24.06, nach Deploy)
- Büro Würzburg 5.000 m² (alte Regel → standard 380 €) → Berichterstellung **119 €**, Gesamt 4.445,85 €
- Krankenhaus München 20.000 m², 30 UV/5 HV (alte Regel → komplex 550 €) → Berichterstellung **119 €**, Gesamt 14.790,29 €
- Beide live über UI bestätigt (`tuev-smartcal-web.fly.dev`).

## Offen (Ball bei S. Pausch)
- **Hipp Kat 2 vs 3** (0800 Produktion) — `KAT_PRODUKTION_0800` = 1-Zeilen-Flip, wartet auf Entscheidung.
- **OP/Intensiv:** Anzahl-Intensivplätze-Ansatz vs. angehobene m²-Rate (KAT_7=8,00) — Rückfrage offen.
