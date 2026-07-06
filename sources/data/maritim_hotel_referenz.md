---
quelle: 1982_001.pdf (Maritim Standortliste) + Anlage B Equipmentliste 2025-2026.pdf
typ: referenz_preisliste
gebaeudetyp: hotel
relevant_fuer: Test 6 (Maritim Königswinter, MA510)
---

# Maritim Hotel — Referenzdaten (To-Do #11)

## Datei 1 — 1982_001.pdf (Standortliste)
Stammdatenliste Maritim Hotelgesellschaft, 30 Standorte + handschriftl. Zimmeranzahl.
Keine Preise. Auszug: **Königswinter (KWI) = 248 Zimmer** (= Test 6), Berlin 505, Bonn 410,
Frankfurt Messe 542, München 349. Spanne 89–555 Zimmer.

## Datei 2 — Anlage B (Rahmenvertrag-Preisanhang, unterzeichnet, gültig 1.1.2025–31.12.2026)
**Bemessung = pro Anlage/Equipment (Stück), NICHT m².** Jede Position = konkretes Gerät mit EQ-Nr.

**Es ist KEIN DGUV-V3-Flächenkatalog** — baurechtliche/anlagentechnische Prüfungen:
Aufzüge (HP+ZP), Veranstaltungstechnik (Bühne), Druckbehälter, **el. Anlage Baurecht 510-WP**,
Sicherheitsbeleuchtung 513, Sicherheitsstromversorgung 511, BMA 583, RLT 419, RWA, Blitzschutz 575.

**Beispiel-Einzelpreise (2025/2026):**
| Position | Einheit | Preis € |
|---|---|---|
| Personenaufzug HP | je Aufzug | 489–668 |
| Personenaufzug ZP | je Aufzug | 182–376 |
| **el. Anlage Baurecht (510-WP)** | **je Anlage** | **12.489 (Bonn) / 15.079 (Düsseldorf) / 17.936 (Köln)** |
| Sicherheitsbeleuchtung 513-WP | je Anlage | 4.586–6.701 |
| BMA 583-WP | je Anlage | 4.606–14.804 |
| RLT 419-WPBA | je Anlage | 6.924–23.715 |

**Gesamtpreise pro Objekt (alle Gewerke):** Bonn 121.878 €, Köln 147.171 €,
**Königswinter 45.669 €**, München 36.417 €, … Summe 924.686 €.

## Kernfrage Test 6: SmartCal 4.063 € vs. Referenz 220 €
1. **Die 220 €-Referenz ist defekt** (Pausch: "Abrechnung fehlerhaft"; bereits xfail/OOS markiert).
   Für ein 10-seitiges Baurecht-Gutachten unmöglich.
2. **Echter Maßstab:** Königswinter Gesamtobjekt 45.669 €; die einzelne **MA510-Baurechtsposition
   allein ~12–18 k €** (vergleichbare Häuser Bonn/Düsseldorf/Köln).
3. **Warum SmartCal daneben lag:** 4.063 € kamen aus dem **DGUV-V3-Flächenmodell** — falscher
   Pfad. MA510 ist eine **baurechtliche Einzelanlagen-Prüfung pro Anlage (12–18 k €)**, kein
   Fläche×Kategorie-Produkt. MA510 ist offiziell außerhalb PoC-Scope.

## Pricing-Regeln Hotel
- **MA510 (510-WP Baurecht) ist KEIN m²-Produkt** → eigener Pfad, pro Anlage, 12–18 k €.
  Code routet Hotel aktuell ins DGUV-Flächenmodell = Fehlerursache.
- Preistreiber Hotel = **Anzahl + Art der techn. Anlagen** (Aufzüge, BMA, RLT,
  Sicherheitsbeleuchtung, Bühne), NICHT Zimmerzahl/Fläche. Königswinter (248 Zi, 45.669 €)
  vs. Bonn (410 Zi, 121.878 €) korreliert mit Anlagenbestand, nicht linear mit Zimmern.
- **Noch ausstehend (To-Do #11):** Motel One (via Philip Steinberger), Krankenhaus-Listen (VTBs,
  Kai Eiden / Benjamin Bachmeier BY).
