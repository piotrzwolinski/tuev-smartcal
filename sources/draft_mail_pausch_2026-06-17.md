---
typ: draft_mail
an: Stefan Pausch
von: Piotr
datum: 2026-06-17
zweck: Faktische Rückfragen + fehlende Daten vor Freitag 20.06. — maximaler Fortschritt vorab
---

**Betreff:** SmartCal — 5 kurze Rückfragen + fehlende Daten (damit ich vor Freitag noch einbauen kann)

Hallo Stefan,

das Modell ist seit letzter Woche an einigen Stellen nochmal nähergekommen — **Krankenhaus**
(eure NetInform-Komplexitätsfaktoren sind übernommen) und die **ortsveränderlichen MA560-Fälle**
(Auto Service, Max Planck Rechenzentrum) liegen jetzt im grünen Bereich.

Damit ich **vor Freitag** noch möglichst viel einbauen kann, ein paar **kurze Rückfragen**, die
sich gut per Mail beantworten lassen — danach kann ich direkt kalibrieren:

**1. Lebensmittel → Kategorie 2 oder 3?**
Test 1 (Hipp) liegt aktuell ~52 % zu hoch. Zählt Lebensmittel-/Genussmittelproduktion (VdS-Code
0800) zu **Kat 2** oder **Kat 3**? (Wir rechnen aktuell Kat 3, vermuten aber, dass Kat 2 näher dran ist.)

**2. REWE-Referenz — welcher Wert gilt?**
Die 2022er-Liste nennt **562 €** (bis 2.000 m²) / **848 €** (2.001–5.000 m²), deine Excel (Test 2)
nennt **657 €**. (a) Welcher Wert ist die belastbare Referenz? (b) Gilt die REWE-Liste **nur für REWE**
oder generell für **Einzelhandel/Kaufhäuser** (VdS 0904)?

**3. Krankenhaus-Sonderbereiche (OP/Intensiv) — woran festmachen?**
OP- und Intensivbereiche sind deutlich aufwändiger als Normalstationen. Da wir ja **weg von der
reinen m²-Logik** wollen: woran sollten wir den Mehraufwand festmachen — eher **Anzahl OP-Säle /
Intensivplätze**? Und wie viel höher liegt so ein Bereich grob im Aufwand gegenüber einer
Normalstation (Richtung Faktor ~1,5× oder ~2×), bzw. gibt es einen Richtwert **je OP-Saal /
je Intensivplatz**?

**4. Zwei Abrechnungen bestätigen:**
Test 5 (Landwirt, 174,80 €) und Test 6 (Maritim Hotel, 220 €) — kannst du bestätigen, dass das
**fehlerhafte Abrechnungen** sind? Falls ja, gibt es die korrekten Werte? (Beim Maritim gehen wir
aus der Rahmenvertragsliste von ~12–18 k€ für die MA510-Anlage aus.)

**5. VdS-Branchen → Kategorie gegenchecken:**
Ich habe die VdS-Nutzungsartenliste aus dem Call (0001–0909) übernommen und jeder Branche eine
Installationskategorie zugeordnet. Passt das grob? Konkret unsicher bin ich bei:
- 0800 Nahrungsmittel (siehe Frage 1)
- 0904 Kauf-/Warenhäuser = Kat 3?
- 0905 ist ein Sammelcode (Krankenhaus + Pflege + Kita) — sollen wir das nach Untertyp splitten?
(Tabelle schicke ich dir gern separat / liegt im Datenraum.)

---

**Daten, die uns noch fehlen** (gern auch schon vor Freitag, falls machbar):

- **Reale Auftrags-/Abrechnungspreise zu den ZF-EQ-Nummern** (oder ein SAP-Export). Die Prüfberichte
  selbst enthalten keinen Preis — ohne die realen Preise können wir die Industrie-Anlagen nicht gegen
  das Modell validieren. (ggf. mit Markus)
- **Original-Angebot Helios Klinik Pasing** (VdS/DGUV-Kombi) — zur Erklärung der Kombi-Abweichung.
  (über Holger / Matthias)
- **Preislisten Motel One** (Philip Steinberger) und **Krankenhäuser** (über Christoph Theilen).

---

**Für Freitag bringe ich die größeren Themen strukturiert mit** (die brauchen Diskussion, nicht
Mail): eigener Industrie-Pfad ja/nein, Nutzungstyp→Preisliste-Routing, Anwendung der
Komplexitätsfaktoren (Schwelle/multiplikativ) und die MA560-„Klein"-Definition (mit Stefan Veit).

Danke dir — bis Freitag!
Viele Grüße
Piotr
