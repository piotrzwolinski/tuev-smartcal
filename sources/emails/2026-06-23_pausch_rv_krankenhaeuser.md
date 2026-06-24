# S. Pausch / J. Wagler — weitere RV-Preislisten Krankenhäuser (23.06)

**Thread:** C. Theilen (12.06) → J. Wagler (22.06) → S. Pausch leitet weiter (23.06 9:53) + Nachtrag (23.06 9:55).
**Anhänge:** `data/files/rv_krankenhaeuser_24_06/` — 3 xlsx (Schmieder, Schwarzwald-Baar, ZÜS/Diakonie).

## ⭐ Strategischer Kontext (C. Theilen 12.06, wörtlich)
> „Der Kollege S. Pausch ist in dem Projekt des **GLFD EG für die Automatische Preisgestaltung per KI** dabei. Er benötigt **reale Preise aus real existierenden RV für Krankenhäuser, um die KI zu trainieren/verifizieren**."

→ Bestätigt: **unsere Kalibrier-Pipeline ist genau der Projektkern.** S. Pausch sammelt aktiv Krankenhaus-RV genau dafür.

## J. Wagler (22.06): 3 Krankenhaus-RV „wiederkehrend"
a) Kliniken Schmieder · b) Schwarzwald-Baar Klinikum · c) Diakonissen Krankenhaus Stuttgart (will **Jahresgebühr**, um Spitzen bei Prüfumfängen zu vermeiden — Abstimmung je Anlage „sehr aufwändig"). Rückfragen erst ab 29.06 (Urlaub).

## S. Pauschs eigene Einordnung (23.06 9:55, wörtlich)
> „Kliniken Schmieder hatten wir schon, **die anderen haben keine Inhalte für den aktuellen Case (Elektroprüfung)**… Sorry für das Email-spamming."

## Verifiziert (Inhalts-Check)
| Datei | Elektro-relevant? |
|---|---|
| **Schmieder xlsx** (strukturiert, „Tabelle1" + „was ändert sich ab 2025") | ✓ aber **= bekannt** (6 EQ 3602 VdS bestätigt, inkl. Gailingen 1267027 + Gerlingen 2122745; Turnus 4 J). Sauberere Quelle als die PDF. |
| **Schwarzwald-Baar** (Projektübersicht 2020-24) | 1 Elektro-EQ (12609312, VdS 3602, Villingen 78052) — **aber keine Preisspalte** (Aufzug-lastige Übersicht); EQ **nicht im 505-Faktura-Export** → kein nutzbarer Preis. |
| **ZÜS/Diakonie Stuttgart** (290 Z.) | **nein** — nur Aufzug/Druckbehälter (ZÜS), kein Elektro. Out of scope. |

## Fazit
**Keine neuen Elektro-Kalibrier-Stützstellen** (S. Pausch hat recht). Schmieder-Campus-EQ sind RV-flat-Listenpreise (nicht im per-Anlage-Faktura-Export — auch Konstanz-Kontrolle fehlt) → bereits in der Pipeline (`SCHMIEDER_505`). Wert: (a) Bestätigung Projektkern = KI-Preisgestaltung, (b) Schmieder-EQ vollständig (6/6), (c) Krankenhaus-Elektro-RV ist **rar** — Kalibrierung muss primär über 507/560-Faktura (8k/3,6k) + Merkmale laufen, nicht über Krankenhaus-RV-Listen.
