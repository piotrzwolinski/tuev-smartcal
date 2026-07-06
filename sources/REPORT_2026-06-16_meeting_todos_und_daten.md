# Raport: Meeting 15.06. + eingegangene Daten → To-Dos & sofort Umsetzbares

**Datum:** 2026-06-16 · **Basis:** Meeting-Protokoll Pausch (16.06. 09:25) + 6 Daten-Mails
(12.–15.06.) + 11 Anhänge · **Zweck:** Verifikationsgrundlage vor Implementierung.
**Nächste Termine:** Fr 20.06. 10:00 · Di 23.06. 09:00. **AL-Tagung:** 30.06.–02.07.

Surówka (Quellen) abgelegt unter `sources/emails/` (7 Mails) und `sources/data/`
(4 Extrakt-Dokumente + `files/` mit 11 Original-Anhängen, 8 MB).

---

## 1 · Konsolidierte To-Do-Liste (aus Pausch-Protokoll)

Status laut Mail: 🟢 erledigt · 🟡 teils · 🔴 offen. „Daten da?" = liegt uns das Material
jetzt vor.

| # | To-Do | Owner | Status | Daten da? | → unsere Aktion |
|---|-------|-------|--------|-----------|-----------------|
| 1 | Statusmail an Veit/Roebel | Pausch | 🟢 | — | — |
| 2 | Excel-Liste +3-4 neue Beispiele | Pausch | 🟢 (läuft) | ✅ Test 8 da, weitere folgen | Testfälle pflegen, Modell gegen O-Spalte kalibrieren |
| 3 | MA560 „Klein"-Definition + Blitz-Mindestsatz 119 € | Pausch+Veit | 🟡 | ❌ Definition fehlt | **warten** auf interne Def.; Frage Fr 20.06. |
| 4 | VdS-Nutzungsartenliste an Piotr | Pausch | 🟢 (Screenshots) | ✅ als Screenshots | Screenshots → `sources/` ablegen (TODO Piotr), in NUTZUNG_ZU_KATEGORIE mappen |
| 5 | Helios Klinik Pasing Original-Angebot (VdS/DGUV-Kombi-Abweichung) | Pfeifer | 🔴 | ❌ | **warten** auf Holger |
| 6 | Termine Fr 20./Di 23. einstellen | Pausch | 🟢 | — | — |
| 7 | ZF-Konglomerat Industriereferenz | Pausch | 🟢 | ✅ 4 PDF + XLSM | siehe §3.4 (Industrie-Pfad) |
| 8 | REWE-Preisliste | Pfeifer | 🟢 | ✅ PDF | siehe §3.3 (Einzelhandel-Staffel) |
| 9 | NetInform-Komplexitätsfaktoren | Pfeifer | 🟢 | ✅ in Mail | **siehe §3.1 — sofort umsetzbar** |
| 10 | RV-Übersichten nach weiteren Industriebeispielen | Pfeifer+Pausch | 🔴 | teilw. (ZF) | ZF schon nutzbar; weitere abwarten |
| 11 | Hotel- (Motel 1) + Krankenhaus-Listen via Theilen | Pfeifer | 🔴 | teilw. (Maritim da) | Maritim nutzbar (§3.5); Motel One/Kliniken offen |
| 12 | AutoService-Preisliste (DGUV/VdS/Kombi) | Pfeifer | 🟢 | ✅ PDF | siehe §3.2 + §3.3 (Kombi-Regel) |
| 13 | **UI-Fehler in SmartCal bis AL-Tagung** | **Piotr** | 🔴 | — | **eigener Arbeitsblock, §4** |
| 14 | Kaufm. Daten aus SAP | Pausch+Markus | 🔴 | ❌ | **warten** |

---

## 2 · Eingegangene Daten — Was liegt vor

| Quelle | Typ | Kerninhalt | Extrakt |
|--------|-----|-----------|---------|
| Testkalkulationen_Übersicht.xlsx | Ground Truth | 8 Testfälle: SmartCal (N) vs. Ist-Preis (O). Nur T4 & T8 grün. | `data/testkalkulationen_uebersicht.md` |
| EQ3295815 MA507-WP.pdf | Prüfbericht | Grundschule Würzburg = Test 8, 2 Prüftage, ~10 UV, 46 Mängel | dito |
| NetInform-Komplexitätsfaktoren (Mail) | Pricing-Regel | 7 Gebäudetypen → Faktor 1,0–2,0 | `emails/...komplexitaetsfaktoren.md` |
| 4× ZF PDF 2026 + XLSM | Industrie-Referenz | VdS+DGUV pro Werk; Geräte-EPs bottom-up; DGUV≈25% VdS | `data/zf_industrie_referenz.md` |
| Autohaus-Kooperation PDF | Referenz-Preisliste | m²-Staffel × {VdS, DGUV, Kombi}; Kombi≈DGUV×1,5 | `data/autohaus_rewe_preislisten.md` |
| REWE 2022 PDF | Referenz-Preisliste | Einzelhandel 2 m²-Staffeln; MA560 Pauschale+je-Gerät | dito |
| Maritim 2 PDF | Hotel-Referenz | MA510 Baurecht pro Anlage 12–18k €; 220€-Referenz ist defekt | `data/maritim_hotel_referenz.md` |

---

## 3 · Was wir HEUTE implementieren können (sofort, ohne Rückfragen)

> Pflichtregel CLAUDE.md §2: vor jeder Pricing-Änderung `graphify affected`/`explain`
> laufen lassen und betroffene Testfälle benennen. Pro Änderung **ein** Commit + grüner Lauf.

### 3.1 🟢 PRIO 1 — Komplexitätsfaktoren per Gebäudetyp (To-Do #9)
**Was:** Aktuell binär `KOMPLEXITAET_FAKTOR = 1.25`, nur für `{KRANKENHAUS,
VERSAMMLUNGSSTAETTE}` > 10.000 m² (`pricing_rules.py:100-105`, `:286-293`). NetInform liefert
eine **offizielle** per-Typ-Tabelle:

| Gebäudetyp | NetInform-Faktor | aktuell im Code |
|---|---|---|
| Büro | 1,0 | 1,0 |
| Misch (Einzelhandel/Büro/Ärzte/Wohnen) | 1,5 | 1,0 |
| Lehranstalten (Schule/Uni) | 2,0 | 1,0 |
| Betreuung (Lebenshilfe/Altenheim) | 1,5 | 1,0 |
| Hotel | 1,5 | 1,0 |
| Krankenhaus | 2,0 | 1,25 (nur >10k m²) |
| Logistik | 1,0 | 1,0 |

**Umsetzung:** `KOMPLEXITAET_FAKTOR_TYP`-Dict einführen, `_g_komplexitaet` darauf umstellen
(Graph-first mit Python-Fallback wie bei `_g_kat_preis`). Schwelle 10.000 m² entfällt /
wird optional.
**Betroffen (graphify affected `_g_komplexitaet`):** `dguv_pruefkosten()`, `vds_pruefkosten()`,
`GraphPricingEngine`. **Testfälle prüfen:** Schule (Test 8, +23%→Faktor 2,0 erhöht weiter →
**Vorsicht, T8 ist schon grün** — Faktor 2,0 würde T8 überschätzen! Kalibrierung nötig),
Krankenhaus-Tests in `test_dguv_v3.py`. → **Erst Wirkung auf T8 prüfen, dann committen.**

### 3.2 🟢 PRIO 2 — Kombi-Regel DGUV+VdS ≈ DGUV × 1,5 (To-Do #12)
**Was:** Autohaus-Liste zeigt Kombi = DGUV×1,5 (große Flächen) bzw. DGUV+VdS −10% (kleine).
ZF bestätigt: **DGUV nie ohne VdS, DGUV ≈ 25% der VdS-Summe.** Bezug zum bekannten Bug
„VdS double-charge" (Testrunde 08.06). Relevant für Test 1 (+73%), Test 7 (−78%).
**Umsetzung:** Kombi-Pfad in `vds_pruefkosten()`/`dguv_pruefkosten()` als Bündel statt
additiv. **graphify explain "Kombi"/"VdS double-charge" vor Edit.**

### 3.3 🟢 PRIO 3 — Einzelhandel/Supermarkt-Staffel kalibrieren (To-Do #8, betrifft Test 2)
**Was:** Test 2 (REWE Markt, MA507) SmartCal 2.125 € vs. Ist 657 € (+223%). REWE-Liste:
≤2.000 m² = 562 €, 2.001–5.000 m² = 848 € (VdS/DGUV-Wechselpreis). Unser m²-Kat-Modell
überschätzt Einzelhandel massiv.
**Umsetzung:** Verkaufsstätten-Rate / Degression gegen REWE-Anker kalibrieren. **Achtung:**
REWE = Großkunden-RV 2022, Autohaus = LPV 2026 → nicht 1:1, Niveau-Unterschied dokumentieren.
**graphify affected "flaechenkosten_degressiv" + "_g_kat_preis" vor Edit.**

### 3.4 🟡 PRIO 4 — Industrie-Pfad (bottom-up Geräte) als Konzept (To-Do #7)
**Was:** ZF zeigt: Industrie-DGUV = Σ(Geräteanzahl × Geräte-EP)/Zyklus — **m² ist NICHT
der Treiber**. Betrifft Test 1 (+73%) und Test 7 (−78%, Metallverarbeitung stark unterschätzt).
**Heute umsetzbar:** Geräte-EP-Anker als Konstanten/Graph-Nodes hinterlegen (NS-Verteiler
55,58 / Stromkreis m. RCD 11,02 / MS-Trafo 55,58 / MS-Schaltfeld 111,15 / Sicherheitsleuchte
11,12 / Blitz-Ableitung 18,40; Stundensatz 197 €; Anlagenprüfung 60 €). **Voller bottom-up-Pfad =
größerer Umbau** → nur Daten/Konstanten anlegen, Pfad in Fr-Termin abstimmen.

**NEU — 58 ZF-Prüfberichte (84 MB) eingegangen** (`data/zf_pruefberichte_analyse.md`):
12 Anlagen, 3 Standorte, Längsschnitt 2018–2026, EQ-Nrn = exakt die der Preisliste →
**verknüpfbar zu echtem Ground-Truth-Set Industrie.** Kernbefund: Berichte enthalten
**weder Preis noch m²**, aber zuverlässig **Prüfdauer (Std.), Trafo-kVA, Gefährdungskategorie
(a–d), Mängelzahl**. Empirisch: **Preis ≈ Prüfdauer × ~197 €/h** (4 Std→2.293 €, 80 Std→18.557 €).
→ stützt einen **Aufwands-/Stundenpfad** für Industrie zusätzlich zum Geräte-bottom-up.
Heute: EQ↔Preis-Join anlegen; Batch-Feature-Extraktion (Haiku) der 55 Befundscheine vorbereiten
(Fr abstimmen, Pricing-Frage #2).

### 3.5 🟡 PRIO 5 — Hotel-Routing (MA510) entkoppeln (To-Do #11, Test 6)
**Was:** Test 6 (Maritim) wird fälschlich ins DGUV-Flächenmodell geroutet → 4.063 €. MA510
ist baurechtl. Einzelanlagen-Prüfung (12–18 k €), außerhalb PoC-Scope; 220€-Referenz ist
nachweislich defekt (bereits xfail).
**Heute umsetzbar:** (a) Scope-Guard so, dass MA510 gar nicht erst über das Flächenmodell
rechnet; (b) Referenz im Testrunden-Doc auf „220 € defekt — echter Maritim-RV 12–18 k €"
korrigieren. Bleibt xfail/OOS, aber dokumentiert.

### 3.6 🟢 Quick — VdS-Nutzungsarten ergänzen (To-Do #4)
Screenshots der VdS-Nutzungsartenliste in `sources/` ablegen (Piotr hat sie) und fehlende
Nutzungen in `NUTZUNG_ZU_KATEGORIE` / Graph-`NutzungsMapping` ergänzen.

---

## 4 · UI-Block (To-Do #13, Owner Piotr) — bis AL-Tagung 30.06.

Eigenständig, kein TÜV-Input nötig. Konkrete Fehlerliste muss noch aus letzter Demo/Testrunde
gezogen werden (separater Durchgang). **Höchste Termin-Priorität** neben PRIO 1.

---

## 5 · Blockiert / Warten auf Input

| # | Was | Wartet auf |
|---|-----|-----------|
| 3 | MA560-„Klein"-Definition, Blitz-Mindestsatz 119 € | interne TÜV-Definition (Pausch/Veit) |
| 5 | Helios Klinik Pasing Original-Angebot | Holger / Pfeifer |
| 10 | weitere Industriebeispiele | Pfeifer/Pausch RV-Recherche |
| 11 | Motel One + Krankenhaus-Preislisten | Theilen / Steinberger / Eiden / Bachmeier |
| 14 | Kaufm. SAP-Daten | Pausch / Markus |

---

## 6 · Offene fachliche Fragen für Fr 20.06. 10:00

1. **Schul-Faktor:** NetInform sagt Schule = 2,0×. Test 8 (Schule) ist bei aktuell 1,0×
   schon +23%. 2,0× würde überschätzen. → Wirken die NetInform-Faktoren **multiplikativ
   auf den m²-Preis** oder ersetzen sie die Kategorie-Logik? Wie kombiniert mit Kat-1-7?
2. **Industrie m² vs. Geräte:** Soll der Industrie-Pfad (ZF, bottom-up Geräte) als eigener
   Produktzweig rein, oder bleibt PoC bei m²+Pauschalen? (Test 1/7 hängen daran.)
3. **DGUV-25%-Regel:** Gilt „DGUV ≈ 25% der VdS-Summe" generell oder nur Industrie/ZF?
4. **Preisniveau-Mix:** REWE 2022 vs. Autohaus 2026 vs. ZF 2026 — welches Niveau ist
   Kalibrierungs-Referenz? (Inflation ~4% p.a. bereits im Code.)

---

## 7 · Empfohlene Reihenfolge (heute)

1. **§3.1 Komplexitätsfaktoren** — Dict + Graph, **aber** zuerst Wirkung auf Test 8/Schule
   prüfen (Frage 6.1 ggf. Fr klären). Wenn Schul-Faktor 2,0 T8 kaputtmacht → nur Hotel/Misch/
   Betreuung (1,5) + Krankenhaus (2,0) übernehmen, Schule vorerst auslassen.
2. **§3.6 VdS-Nutzungsarten** + Screenshots ablegen (risikolos).
3. **§3.5 Hotel/MA510 Scope-Guard + Doku-Fix** (risikolos, T6 schon xfail).
4. **§3.3 Einzelhandel-Kalibrierung** (Test 2) — ein Commit, gegen Golden-Set verifizieren.
5. **§3.2 Kombi-Regel** — heikel (VdS double-charge), sorgfältig + voller Testlauf.
6. **§3.4 Industrie-Konstanten** anlegen (Daten, kein Pfad) — Pfad Fr abstimmen.
7. **§4 UI-Fehler** — parallel, eigener Block.

Jeder Schritt: `graphify affected/explain` → betroffene Testfälle nennen → ändern →
`pytest tests/ -q --ignore=tests/test_e2e_llm_judge.py` + `scripts/test_testrunde1_all.py`
→ Zahlen in Commit.
