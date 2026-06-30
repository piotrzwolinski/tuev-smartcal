# S. Pausch — Berichterstellungskosten 119 / 550 € (Regel)

**Quelle:** Mail S. Pausch, 17.06.2026 10:34 (Antwort auf Piotrs Rückfragen zur Berichterstellung).
**Stand:** umgesetzt 24.06 (Engine `dguv_choose_bericht_typ`).

---

> Hallo Piotr,
>
> zu deinen Fragen siehe meine Anmerkungen in Rot.
>
> **Weitere Infos von Stefan und mir:**
>
> **Kosten Prüfberichte:**
> Bisher wurden diese Preisfaktoren so gut wie nicht angezogen, d.h. bei der Mitkalkulation
> dieses Faktors werden wir tendenziell höher ausfallen als die bisherigen Angebote. Ist nicht
> schlimm, geben wir weiter so aus als **Baustein** (obliegt dem Angebotsersteller, ob er es mit
> anzieht bzw. ins Angebot übernimmt).
>
> **Generell:** für die Materialien Blitzschutz und Elektroprüfung (DGUV, VdS) setzen wir hier
> **immer den kleinen Bericht an, mit 119 €**. Die **komplexen Berichte** für die Prüfung nach
> **Baurecht und Elektrothermographie** (hier haben wir auch einen tatsächlich höheren Aufwand).
> Sollte der Kunde **spezielle Anforderungen** an die Prüfberichte haben (wäre abzufragen, z.B.
> eigene Form, Sonderform der Übermittlung), dann ziehen wir auch die Kosten für den komplexen
> Bericht an (mehr Leistung = mehr Kosten).
>
> VG
> Stefan

---

## Regel (destilliert → Engine)

- **DGUV / VdS / Blitz → immer kleiner Bericht 119 €** (keine Fläche/Verteilungen-Staffel).
- **Komplexer Bericht 550 €** nur bei: **Baurecht**, **Elektrothermographie**, **Kunden-Sonderanforderung**
  (eigene Form / Sonderform Übermittlung — abzufragen).
- **„Standard 380 €" entfällt** für diese Materialien.
- Charakter: **Baustein** — optional, Angebotsersteller entscheidet. Treibt Preise ggü. historischen
  Angeboten (die den Faktor kaum anzogen) tendenziell nach oben — „ist nicht schlimm".

## Umsetzung (24.06)
- `dguv_choose_bericht_typ` neu: inklusive (RV-Flat/Kleinauftrag/ortsveränderlich) → klein 119 →
  komplex 550 bei `baurechtlich | elektrothermographie | bericht_sonderanforderung`.
- Neue Merkmale-Flags `elektrothermographie`, `bericht_sonderanforderung` (default False).
- **Impact** (`scripts/impact_berichterstellung.py`): 7/12 Golden-Fälle ändern sich, alle nach
  unten (−261…−431 €), **5 näher an real** (T01 +17→+10%, T12 +17→+14%, T14 +19→+8%, T15 +11→+5%),
  0 Regressionen; RV-Flat/Kleinauftrag/MA560 unberührt. Tests grün (554 passed).
