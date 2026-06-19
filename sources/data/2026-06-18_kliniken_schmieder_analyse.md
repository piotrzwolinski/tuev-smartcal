# Kliniken Schmieder — VdS-Krankenhaus-Referenz (RV 19110252_4, 2025–2027)

**Quelle:** `files/2026-06-18_Anlage1_Preise_Kliniken_Schmieder_2025-2027.pdf` (Pfeifer 18.06).
**Strukturierter Datensatz:** `schmieder_full.csv` (90 Positionen, 6 Standorte × alle Gewerke;
Builder `build_schmieder_csv.py` — **verifiziert gegen die PDF-Zwischensummen** innerhalb
PDF-Rundungstoleranz). Nur **6/90 Zeilen in DGUV/VdS-Scope** (el. Anlage 3602 VdS), 84 =
baurechtliche Gewerke (Aufzug 39×, Nat.Rauchabzug 10×, BMA 8×, SiBe 8×, Druck, Lüftung…).
**Bedeutung:** Reale **VdS-Elektroprüfungs-Preise für Kliniken** (6 Standorte) — Krankenhaus-Ground-Truth (bisher Lücke: T12 Helios, T14 roMEd). Ergänzt den MA505-Export.

## 1 · Die 6 VdS-Elektro-Anker (el. Anlage 3602 VdS = MA505/Klausel 3602)
Je Standort **eine gebündelte EQ** („Gesamter Standort / alle Häuser"), **4-Jahres-Turnus**:

| Standort | EQ | €/Prüfung (2025-27) | €/Jahr | Site-Gesamt-RV/J* |
|---|---|---|---|---|
| Stuttgart | 2122743 | **655** | 164 | 545 |
| Gerlingen | 2122745 | **2.129** | 532 | 5.501 |
| Konstanz | 1268813 | **2.151** | 538 | 5.346 |
| Gailingen | 1267027 (Master) | **5.445** | 1.361 | 7.200 |
| Allensbach | 1268824 | **5.880** | 1.470 | 11.786 |
| Heidelberg | 1879930 | **5.880** | 1.470 | 8.508 |

\* Site-Gesamt-RV = alle Gewerke (s.u.). **Gesamtsumme alle Standorte: 92.597 € (Turnus) / 38.886 €/J / Quartalsrechnung 9.721 €.**

## 2 · Schlüssel-Befunde
1. **Bundled-Site-RV-Flat:** die VdS-Elektroprüfung deckt je Standort **alle Häuser unter einer EQ** ab (Allensbach = Bodan, Säntis, Höri, Thurgau, Mainau, Lindau, Davos → ein Preis 5.880 €). → Kliniken werden **pro Campus pauschal** bepreist, nicht pro Gebäude summiert (gleiches Muster wie REWE-Filialnetz / A3, aber auf Standort-Ebene).
2. **Liegt im VdS-Korridor (MA505):** 655–5.880 € = ~Median bis ~p95 (MA505 p75=2.045, p90=3.882). Große Klinik-Campus ≈ p95. Konsistent.
3. **EQ-Join offen (Pausch klärt):** was hinter jeder EQ steckt (m², Anzahl Häuser/Anlagen) ist noch aufzulösen — erst dann **Krankenhaus-VdS = f(Campus-Größe)** kalibrierbar. Heute = Anker ohne Merkmale.
4. **Elektro = ~10–15 % der Klinik-RV-Summe.** Rest (out of PoC-Scope) = Aufzug (382 €/Anlage Standard), BMA, SiBe, Druckbehälter, Nat.Rauchabzug, Lüftung, Garage — alles **baurechtliche Einzelanlagen-Prüfung**. Zeigt die volle Multi-Gewerk-RV-Struktur (relevant für MVP-Bundling F1) + **Quartalsrechnung** als Abrechnungsmodell.
5. **Cross-Check MA505-Export:** keine der 6 EQ im 505-Export (4-J-Turnus → außerhalb Versand-Fenster) → **6 unabhängige zusätzliche Anker**.

## 3 · Was wir damit tun können
| # | Aktion | Aufwand | Voraussetzung |
|---|---|---|---|
| S1 | **6 VdS-Klinik-Anker** in Referenz/Envelope dokumentieren (Krankenhaus-VdS 655–5.880 €/Campus) | klein | nichts |
| S2 | **T12/T14 plausibilisieren** gegen Klinik-VdS-Range (Helios-Kombi 13.110 > VdS-only-Max 5.880 ✓ kombi+groß; roMEd ~5.136 ≈ oberer Rand) | klein | nichts |
| S3 | **Bundled-Campus-Logik** für Klinik-Multi-Standort dokumentieren (pauschal pro Campus, nicht pro Gebäude summieren) | mittel | Routing-Entscheid |
| S4 | **Krankenhaus-VdS-Kurve kalibrieren** per EQ→Campus-Merkmale | groß | **Pausch löst EQ auf** (läuft) |
| S5 | Multi-Gewerk-RV-Struktur als MVP-Bundling-Referenz (F1) ablegen | — | MVP-Scope |

**Limitierung:** wie MA505 — Preise ohne Anlagenmerkmale. Aber Pfeifer/Pausch lösen die EQ gerade auf (Mail) → dann S4. **Sofort sinnvoll: S1 + S2** (Anker + Plausibilisierung, datengetrieben). **S4** = der Hebel, sobald EQ-Auflösung da ist.
