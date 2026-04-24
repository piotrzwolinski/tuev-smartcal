# Synapse OS for TÜV Süd — SmartCal@EG
## 12-Week Project Plan (KW14–KW25, April–June 2026)

**MVP Demo: KW27 (06.07.2026) — Abteilungsleitertagung**
**Buffer: 1 Woche vor Demo für Stabilisierung & Rehearsal**

---

## Phase 1: Foundation (KW14–KW16) — 3 Wochen

### KW14 — Daten & Setup
- [ ] Kick-off Workshop mit TÜV (Pausch + Pfeiffer)
- [ ] Übergabe der Dokumente: Inspektionsberichte, Angebotsanfragen, fertige Angebote, LPV
- [ ] Auswahl der 3 Startprodukte (z.B. Elektrische Anlage, Entrauchung, Wallboxen)
- [ ] Aufsetzen Projekt-Infrastruktur (Repo, CI/CD, Staging)
- [ ] **AI-Extraktion Pipeline aufbauen**: LLM-gestützte Analyse der TÜV-Dokumente
  - Inspektionsberichte → Prüfmerkmale, Zeitaufwände, Objekttypen
  - Angebote → Preispositionen, Staffeln, Zuschlagsregeln
  - Angebotsanfragen → typische Kundeninputs, Gebäudemerkmale

**Deliverable:** Projektsetup, Extraktions-Pipeline, erster Regelentwurf aus echten Dokumenten
**Benötigt von TÜV:** Dokumente (Inspektionsberichte, Anfragen, Angebote, LPV) — kein manuelles Aufbereiten nötig, wir extrahieren automatisch

### KW15 — Knowledge Graph v1 (aus extrahierten Daten)
- [ ] Extrahierte Regeln & Preise → Graph-Schema überführen (Produkt 1)
- [ ] Automatisch erkannte Preispositionen, Staffeln, Merkmale validieren
- [ ] Delta-Review mit TÜV: "Wir haben X extrahiert — stimmt das?"
- [ ] Unit-Tests für Preisberechnung

**Deliverable:** Graph mit echtem Produkt 1, validierte Preisberechnung
**Vorteil:** TÜV muss keine Regeln manuell liefern — wir zeigen ihnen was wir gefunden haben, sie bestätigen/korrigieren nur

### KW16 — Produkte 2 & 3 + Pipeline
- [ ] Extraktion für Produkte 2 & 3 durchführen
- [ ] Graph erweitern, Pipeline-Anpassung für neue Produktstrukturen
- [ ] Reisekosten-Modul (Region, Entfernung, Pauschalen — aus Angeboten extrahiert)
- [ ] Review-Call mit TÜV: Preisvalidierung aller 3 Produkte

**Deliverable:** Alle 3 Produkte kalkulierbar, Reisekosten integriert
**Meilenstein M1: Korrekte Kalkulation der 3 Startprodukte ✓**

---

## Phase 2: UX & Features (KW17–KW20) — 4 Wochen

### KW17 — TÜV Design System
- [ ] TÜV Styleguide / Figma erhalten und analysieren
- [ ] Re-Skin: Farben, Fonts, Logo, Komponenten
- [ ] Login & Benutzerverwaltung (Rollen: Admin, Sachverständiger, Verwaltung)
- [ ] Responsive Layout-Optimierung

**Deliverable:** App im TÜV-Design mit Login
**Benötigt von TÜV:** Styleguide / Brand Assets, gewünschte Benutzerrollen

### KW18 — Schieberegler & Interaktion
- [ ] Schieberegler UI: grob / mittel / fein
  - Grob: nur BGF → Schätzpreis mit Sicherheitsfaktor
  - Mittel: BGF + Basismerkmale
  - Fein: alle Merkmale, Rückfragen-gesteuert
- [ ] Verbessertes Rückfragen-System (strukturiert, nicht nur Chat)
- [ ] Angebotshistorie / Session-Management (persistent)

**Deliverable:** Dreistufige Kalkulation, persistente Sessions

### KW19 — Cross-Selling & Zuschläge
- [ ] Cross-Selling / Empfehlungen-UI (aus EMPFIEHLT-Kanten)
- [ ] Gefahrenzonen-Zuschläge (Krankenhaus +25%, etc.)
- [ ] Bündelrabatte bei Gleiche-Begehung
- [ ] Detailansicht pro Position (Berechnungsgrundlage transparent)

**Deliverable:** Vollständige Preislogik mit Zuschlägen, Rabatten, Empfehlungen

### KW20 — Textbausteine & Export
- [ ] Textbausteine-Generator: Angebots-Text aus Kalkulation
- [ ] PDF-Export der Kalkulation
- [ ] Copy-to-Clipboard für SAP-Übernahme
- [ ] Review-Call mit TÜV: Feature-Demo

**Deliverable:** Exportierbare Angebote
**Meilenstein M2: Feature-Complete MVP ✓**

---

## Phase 3: Qualität & Rollout (KW21–KW23) — 3 Wochen

### KW21 — Testing mit Fachexperten
- [ ] UAT (User Acceptance Test) mit 2–3 Sachverständigen
- [ ] Testszenarien: 10+ reale Kalkulationsfälle durchspielen
- [ ] Abgleich mit manuellen Excel-Kalkulationen
- [ ] Bug-Fixing & Preiskorrekturen

**Deliverable:** UAT-Ergebnisse, Bug-Fixes
**Benötigt von TÜV:** 2–3 Sachverständige als Tester, reale Testfälle

### KW22 — Performance & Stabilität
- [ ] Performance-Optimierung (< 3s für Kalkulation)
- [ ] Error-Handling & Edge-Cases
- [ ] Hosting-Setup (Cloud / TÜV-Infrastruktur?)
- [ ] Monitoring & Logging

**Deliverable:** Produktionsreife Applikation
**Benötigt von TÜV:** Klärung Hosting (Cloud vs. On-Prem)

### KW23 — Feinschliff & Dokumentation
- [ ] UI-Polish basierend auf UAT-Feedback
- [ ] Admin-Bereich: Graph-Daten pflegen (Preise aktualisieren)
- [ ] Benutzerhandbuch / Onboarding-Flow
- [ ] Staging-Deployment für TÜV-Review

**Deliverable:** Staging-Version für finale Abnahme
**Meilenstein M3: MVP Staging-Ready ✓**

---

## Phase 4: Launch-Vorbereitung (KW24–KW25) — 2 Wochen

### KW24 — Abnahme & Demo-Prep
- [ ] Finale Abnahme mit Feith / Pausch / Pfeiffer
- [ ] Demo-Skript für Abteilungsleitertagung vorbereiten
- [ ] Demo-Daten aufbereiten (repräsentative Szenarien)
- [ ] Fallback-Szenarien testen

### KW25 — Go-Live & Rehearsal
- [ ] Produktion-Deployment
- [ ] Demo-Rehearsal mit TÜV-Team
- [ ] Letzte Korrekturen
- [ ] Übergabe-Dokumentation

**Meilenstein M4: MVP Live ✓**

> **KW26:** Buffer-Woche
> **KW27:** Abteilungsleitertagung — Live-Demo

---

## Abhängigkeiten von TÜV

| Was | Wann benötigt | Von wem |
|---|---|---|
| Dokumente: Inspektionsberichte, Anfragen, Angebote, LPV (Rohdaten, kein Aufbereiten nötig) | KW14 | Pausch / Pfeiffer |
| Fachlicher Ansprechpartner für Validierung der extrahierten Regeln | KW15–16 | Pausch |
| Styleguide / Brand Assets | KW17 | Digital Team / Marco Schäfer |
| Benutzerrollen-Definition | KW17 | Feith |
| 2–3 Tester (Sachverständige) | KW21 | Pausch |
| Hosting-Entscheidung | KW22 | IT / Marco Schäfer |
| Demo-Abnahme & Skript-Review | KW24 | Feith |

---

## Risiken

| Risiko | Mitigation |
|---|---|
| Dokumente kommen spät | Parallel mit synthetischen Daten weiterentwickeln, Austausch als Drop-in |
| Preislogik komplexer als erwartet | AI-Extraktion deckt Muster auf, die manuell übersehen würden; wöchentliche Validierungs-Calls |
| Extrahierte Regeln unvollständig | Delta-Review-Ansatz: TÜV korrigiert/ergänzt nur, statt alles manuell zu erstellen |
| TÜV Design System nicht verfügbar | Eigenes TÜV-nahes Design erstellen, später anpassen |
| Hosting-Entscheidung blockiert | Staging auf Minglabs-Cloud, Migration später |
| Scope Creep (weitere Produkte) | Strikt bei 3 Produkten für MVP bleiben |

---

## Team

| Rolle | Person | Verfügbarkeit |
|---|---|---|
| Technical Lead | Piotr Zwolinski | Durchgehend |
| Project Lead / Sales | Matthias Roebel | Steering, Reviews |
| Project Coordination | Katharina Jockenhöfer | Ab KW15 |

---

*Powered by Synapse OS — Minglabs*
