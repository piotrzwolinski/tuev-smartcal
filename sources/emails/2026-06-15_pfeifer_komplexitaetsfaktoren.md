---
quelle: E-Mail Matthias Pfeifer
datum: 2026-06-15 12:52
von: Pfeifer, Matthias
an: Piotr, Stefan
betreff: Komplexitätsfaktoren
typ: pricing_regel
quelle_referenz: netinformRE (Technischer Ausstattungsgrad)
---

# Mail Pfeifer 15.06. 12:52 — "Komplexitätsfaktoren"

> Hier die gezeigten Komplexitätsfaktoren / Technischer Ausstattungsgrad im Rahmen
> von netinformRE:

## Technischer Ausstattungsgrad (Hinweis) — Faktoren

| Gebäudetyp | Faktor |
|------------|--------|
| Büro-Immobilie | **1,0×** |
| Misch-Immobilie (z.B. Einzelhandel, Büro, Ärzte, Wohnen) | **1,5×** |
| Lehranstalten (z.B. Schulen, Universitäten) | **2,0×** |
| Betreuungseinrichtungen (z.B. Lebenshilfe, Altenheim) | **1,5×** |
| Hotel | **1,5×** |
| Krankenhaus | **2,0×** |
| Logistik | **1,0×** |

> Mit freundlichen Grüßen / Kind regards — Matthias Pfeifer

## Kontext / Wert
Bezug zu To-Do #9. **Direkt implementierbar** — ersetzt unseren aktuellen binären
`KOMPLEXITAET_FAKTOR = 1.25` (nur Krankenhaus/Versammlungsstätte > 10.000 m²) durch eine
per-Gebäudetyp-Tabelle. Offizielle TÜV-/netinformRE-Quelle, kein geschätzter Wert.
