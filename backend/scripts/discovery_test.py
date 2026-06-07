"""Test discovery prompt on 10 PDFs."""
import json, random
from pathlib import Path
from pdfminer.high_level import extract_text
import anthropic

client = anthropic.Anthropic()

DISCOVERY_PROMPT = """Du analysierst einen TÜV SÜD Prüfbericht. Extrahiere ALLES was du finden kannst.

{
  "ist_gesamtanlage": true oder false,
  "gebaeudetyp": "Freitext",
  "standort_plz": "PLZ",
  "standort_ort": "Stadt",
  "betreiber_typ": "Kommune oder Firma oder Kirche oder sonstige",
  "betreiber_branche": "Freitext z.B. Lebensmittelhandel, Automobilzulieferer, Bildungseinrichtung",
  "prueftage": Anzahl,
  "seitenzahl": Anzahl,
  "anzahl_uv": Anzahl,
  "anzahl_hv": Anzahl,
  "anzahl_rcd_messwerte": Anzahl,
  "stockwerke_erkannt": ["KG","EG","1.OG"],
  "maengel_anzahl": Anzahl,
  "maengel_max_schwere": "keine oder geringfuegig oder erheblich oder gefaehrlich",
  "grundlage_baurecht": true oder false,
  "nea_vorhanden": true oder false,
  "besondere_ausstattung": ["Aufzug","Turnhalle","Labor"],

  "_discovery": {
    "raeume_typen": {"Buero": 3, "Labor": 2, "Kueche": 1, "Flur": 5},
    "erwaehnte_anlagen": ["Aufzug", "Brandmeldeanlage", "PV-Anlage", "Ladestation", "Sicherheitsbeleuchtung", "Klimaanlage", "Heizung", "RWA", "Sprinkler"],
    "erwaehnte_normen": ["DIN VDE 0100-710", "VDE 0100-420"],
    "messungen_anzahl_zeilen": Anzahl Zeilen in Messtabelle,
    "dokumentation_zustand": "vorhanden_vollstaendig oder vorhanden_unvollstaendig oder nicht_vorhanden oder nicht_erwaehnt",
    "vorheriger_pruefbericht": true oder false,
    "gebaeude_komplex_teile": Anzahl Gebaeudeteile wenn mehrere,
    "baujahr_oder_alter": "Jahr oder Beschreibung",
    "erschwernisse": ["Nachtarbeit", "laufender Betrieb", "Sicherheitsfreigabe noetig", "Zugang eingeschraenkt", "Hoehenarbeit", "Ex-Zone", "Schichtbetrieb"],
    "nicht_geprueft_bereiche": Anzahl Bereiche die nicht geprueft werden konnten,
    "nicht_geprueft_grund": "z.B. nicht zugaenglich, betriebsbedingt nicht schaltbar",
    "anlagen_komplexitaet": Anzahl verschiedener Anlagentypen im Gebaeude (PV+USV+BMA+Aufzug = 4),
    "auffaelligkeiten": ["Freitext - alles was ungewoehnlich ist oder den Pruefaufwand beeinflusst"]
  }
}

NUR valides JSON. Keine Erklaerungen."""

random.seed(77)
pdfs = list((Path.home() / "Desktop/TUEV/507").glob("*MA507*.pdf"))
sample = random.sample(pdfs, 10)

for i, f in enumerate(sample):
    try:
        text = extract_text(str(f), maxpages=6)
        if len(text) < 100:
            continue
        msg = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=1500,
            messages=[{"role": "user", "content": f"Pruefbericht:\n\n{text[:10000]}"}],
            system=DISCOVERY_PROMPT,
        )
        raw = msg.content[0].text.strip()
        if "```" in raw:
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        result = json.loads(raw)

        disc = result.get("_discovery", {})
        typ = result.get("gebaeudetyp", "?")
        branche = result.get("betreiber_branche", "?")
        raeume = disc.get("raeume_typen", {})
        anlagen = disc.get("erwaehnte_anlagen", [])
        normen = disc.get("erwaehnte_normen", [])
        doku = disc.get("dokumentation_zustand", "?")
        auffaellig = disc.get("auffaelligkeiten", [])
        mess = disc.get("messungen_anzahl_zeilen", "?")
        baujahr = disc.get("baujahr_oder_alter", "?")
        komplex = disc.get("gebaeude_komplex_teile", "?")
        vorher = disc.get("vorheriger_pruefbericht", "?")

        print(f"{i+1:2d}. {f.name[:40]}")
        print(f"    Typ: {typ} | Branche: {branche}")
        print(f"    Raeume: {dict(list(raeume.items())[:5]) if raeume else '-'}")
        print(f"    Anlagen: {anlagen[:5] if anlagen else '-'}")
        print(f"    Normen: {normen[:3] if normen else '-'}")
        print(f"    Doku: {doku} | Baujahr: {baujahr} | Mess-Zeilen: {mess}")
        print(f"    Komplex-Teile: {komplex} | Vorher geprueft: {vorher}")
        print(f"    AUFFAELLIG: {auffaellig[:3] if auffaellig else '-'}")
        print()
    except Exception as e:
        print(f"{i+1:2d}. ERROR: {str(e)[:80]}")
