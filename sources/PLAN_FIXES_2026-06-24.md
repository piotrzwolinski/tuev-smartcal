# Fix-Plan 24.06.2026 (vor AL-Tagung)

> Ziel: demo-fähiger, **ehrlicher** Stand bis AL-Tagung. Keine Overfits.
> Grundlage: `PLAN_REPARATUR_2026-06-24.md` (Analyse), Datenbefund: Faktura-Preis ≠ f(Merkmale).

## Prinzip (was wir fixen vs. nicht)
- ✅ **Mechanismus-/Ehrlichkeits-Fixes** (generalisieren für ALLE Inputs) → diese Woche.
- ❌ **Kein Coefficient-Tuning auf Stefans Fälle** (overfit, OOS belegt schlecht) → nicht.
- 🟡 **Datengetriebene Kalibrierung** (MA560-Degression R²=0,78) → Phase 2 (bricht sonst Demo-Fälle).

## Fixes

### F1 · P4 Reifegrad-Halluzination + Anzeige-Mismatch — ✅ DIESE WOCHE
- **Was:** `_strip_hallucinated_reifegrad` (Zwilling zu `_strip_hallucinated_flaeche`) — Reifegrad entfernen, wenn Kunde nichts zu Zustand/Reifegrad gesagt hat → Default RG_3. Zusätzlich: Chat-Summary-Zahl = Engine-Total (kein 562 vs 702 Widerspruch).
- **Generalisiert:** ✅ voll (Bug-Mechanismus, alle Fälle).
- **Effekt:** #9 Supermarkt 702,50 € → **562 € (+0 %)**.
- **Aufwand:** ~1–2 h. **Bug-Catcher-Test:** Supermarkt-Prompt → kein ×1,25.
- **graphify affected** `_g_reifegrad` vor Edit.

### F2 · Listenpreis-Transparenz / RV-Hinweis (P1) — ✅ DIESE WOCHE (umgedeutet)
- **WICHTIGE KORREKTUR (verifiziert 24.06):** „fehlende m²" ist NICHT die Ursache. Beleg: #8 Grundschule (ohne m², „25 Klassenräume" → System schätzt 1.900 m²) trifft real **+5 %**. Gleicher Mechanismus #13 Uni → +104 % — der Unterschied ist **allein der Realpreis** (2.380 vs 1.261 € für ähnliche Gebäude = Vertrag/Rabatt). Die m²-Schätzung funktioniert.
- **Was wirklich richtig ist:** Output klar als **LISTENPREIS** ausweisen + sichtbarer Hinweis „realer RV-Preis kann −46…−85 % darunter liegen — RV/Rabatt bitte separat". KEIN „niedrige Confidence weil kein m²" (wäre falsche Begründung).
- **Generalisiert:** ✅ als Ehrlichkeit/Framing für ALLE Fälle.
- **Effekt:** #13/#14/#15 erscheinen als **Listenpreis mit RV-Caveat** statt als „falscher Endpreis". Macht die Differenz erklärbar, nicht peinlich.
- **NICHT-Effekt:** bringt #13-15 NICHT auf +0 % — der Realpreis ist Vertrag/Rabatt, nicht modellierbar (Phase 2: Kunden-/RV-Dimension).
- **Aufwand:** ~halber Tag (UI-Label + Hinweistext).

### F3 · MA560-Degression (P2) — 🟡 PHASE 2 (nicht vor Tagung)
- **Was:** flat 9,50 €/BM → Degression `≈21·BM^0,76` (R²=0,78, 390 reale Punkte).
- **Warum nicht jetzt:** **Tradeoff** — fixt #12 Landgericht (−10 %), **bricht T04/T10** (−36/−53 %, Demo-Fälle). Restvarianz 9×/Band (24 % OOS).
- **Phase 2:** sauberer Staffel-Ansatz + ggf. Kunden-/Vertragsdimension.

### F4 · Kleinauftrag-Floor (P3) — 🔵 SPÄTER
- 1 Datenpunkt (#16), gleiche Varianz. Floor Merkmale-abhängig — erst mit mehr Daten.

## Was NICHT gemacht wird (bewusst)
- ❌ Per-UV-Koeffizienten (`1.032+95·UV`) einbauen — in-sample, OOS 15 %, overfit.
- ❌ MA560-Modell vor Tagung tauschen — bricht validierte Demo-Fälle.
- ❌ Versuch, Faktura-Preis aus Merkmalen zu treffen — fehlende Variable (Rabat −46…−85 %).

## Reihenfolge
1. **F1 (P4)** heute — Strip + Anzeige-Konsistenz + Test + Deploy.
2. **F2 (Graceful-Uncertainty)** nach S. Pausch-Antwort (fragen vs schätzen) — Deploy.
3. **Demo-Set** (8 validierte) re-testen über UI + Bericht.
4. F3/F4 = Phase-2-Backlog.

## Definition of Done (Tagung)
- [ ] F1 deployed, #9 = 562 € (+0 %), Bug-Catcher grün, voller Lauf grün.
- [ ] F2 deployed, no-m²-Fälle zeigen niedrige Confidence/Rückfrage.
- [ ] 8 Demo-Fälle live über UI bestätigt (Bericht).
- [ ] Strategie-Doc „Stand & Demo" (was/warum) fertig.
- [ ] Keine Demo-Regression (T04/T10/REWE/Apleona unverändert).
