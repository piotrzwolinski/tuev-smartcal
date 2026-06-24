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

### F2 · Graceful-Uncertainty bei fehlendem m² (P1) — ✅ DIESE WOCHE
- **Was:** Wenn DGUV-ortsfest **ohne m²** (nur UV/Merkmale): keine fabrizierte Fläche als belastbaren Preis verkaufen. Stattdessen **niedrige Confidence + sichtbarer Hinweis** „Schätzung aus UV — für belastbare Kalkulation bitte m²/Aufwand angeben". (Variante je nach S. Pausch-Antwort: Rückfrage statt Rechnung.)
- **Generalisiert:** ✅ als Verhalten (Ehrlichkeit für alle no-m²-Fälle). Korrigiert NICHT die Zahl (geht nicht — fehlende Variable).
- **Effekt:** #13/#14/#15 failen **ehrlich** (niedrige Conf.) statt selbstbewusst +60–104 %.
- **Aufwand:** ~halber Tag. Hängt an S. Pausch-Frage „fragen vs. schätzen".

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
