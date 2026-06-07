"""Batch preflight: 200 PDFs per 500er Material → extract key Merkmale."""

import json
import os
import random
import sys
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

from pdfminer.high_level import extract_text
import anthropic

client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

MATERIALS = {
    "MA507": {
        "path": Path.home() / "Desktop/TUEV/507",
        "pattern": "*MA507*.pdf",
        "prompt": """Du analysierst einen TÜV SÜD Prüfbericht DGUV V3 ortsfeste elektrische Anlage (MA507).
Extrahiere als JSON. Null für fehlende Werte.
{
  "ist_gesamtanlage": true/false,
  "gebaeudetyp": "Schule|Büro|Industrie|Krankenhaus|Hotel|Supermarkt|Kirche|Tiefgarage|Versammlungsstätte|Wohngebäude|Kindergarten|sonstige",
  "gebaeudetyp_freitext": "exakter Text",
  "standort_plz": "PLZ",
  "standort_ort": "Stadt",
  "betreiber_typ": "Kommune|Firma|Kirche|Wohnungseigentümer|sonstige",
  "prueftage": "Anzahl (aus Zeitraum berechnen)",
  "seitenzahl": "aus Seite X von Y",
  "anzahl_uv": "Unterverteilungen",
  "anzahl_hv": "Hauptverteilungen",
  "anzahl_rcd_messwerte": "RCD/FI Messzeilen",
  "stockwerke_erkannt": ["KG","EG","1.OG"],
  "errichtungszeitraum": "Jahr",
  "maengel_anzahl": "Anzahl",
  "maengel_max_schwere": "keine|geringfügig|erheblich|gefährlich",
  "grundlage_baurecht": true/false,
  "nea_vorhanden": true/false,
  "besondere_nutzung": ["Labor","Küche","Aufzug"]
}
NUR JSON.""",
    },
    "MA560": {
        "path": Path.home() / "Desktop/TUEV/560 (1)",
        "pattern": "*MA560*.pdf",
        "prompt": """Du analysierst einen TÜV SÜD Prüfbericht DGUV V3 ortsveränderliche Betriebsmittel (MA560).
Extrahiere als JSON. Null für fehlende Werte.
{
  "gebaeudetyp": "Schule|Büro|Industrie|Krankenhaus|Hotel|Supermarkt|sonstige",
  "gebaeudetyp_freitext": "exakter Text",
  "standort_plz": "PLZ",
  "standort_ort": "Stadt",
  "betreiber_typ": "Kommune|Firma|sonstige",
  "anzahl_gepruefte_geraete": "Anzahl geprüfter Geräte/Betriebsmittel",
  "prueftage": "Anzahl Prüftage",
  "seitenzahl": "aus Seite X von Y",
  "maengel_anzahl": "Anzahl",
  "fehlerquote_prozent": "wenn angegeben"
}
NUR JSON.""",
    },
    "MA510": {
        "path": Path.home() / "Desktop/TUEV/510",
        "pattern": "*MA510*.pdf",
        "prompt": """Du analysierst einen TÜV SÜD Prüfbericht Baurecht elektrische Anlage (MA510).
Extrahiere als JSON. Null für fehlende Werte.
{
  "gebaeudetyp": "Schule|Büro|Industrie|Krankenhaus|Hotel|Versammlungsstätte|sonstige",
  "gebaeudetyp_freitext": "exakter Text",
  "standort_plz": "PLZ",
  "standort_ort": "Stadt",
  "bundesland": "aus Landesbauordnung ableiten",
  "prueftage": "Anzahl",
  "seitenzahl": "aus Seite X von Y",
  "anzahl_uv": "Unterverteilungen",
  "grundlage": "welche Verordnung (VStättVO, LBO, SPrüfV etc.)",
  "maengel_anzahl": "Anzahl",
  "besondere_nutzung": ["Sicherheitsbeleuchtung","Brandmeldeanlage","RWA"]
}
NUR JSON.""",
    },
    "MA501": {
        "path": Path.home() / "Desktop/TUEV/501",
        "pattern": "*MA501*.pdf",
        "prompt": """Du analysierst einen TÜV SÜD Prüfbericht freiwirtschaftliche Prüfung elektrische Anlage (MA501).
Extrahiere als JSON. Null für fehlende Werte.
{
  "gebaeudetyp": "Schule|Büro|Industrie|Krankenhaus|Hotel|Supermarkt|sonstige",
  "gebaeudetyp_freitext": "exakter Text",
  "standort_plz": "PLZ",
  "standort_ort": "Stadt",
  "betreiber_typ": "Kommune|Firma|sonstige",
  "prueftage": "Anzahl",
  "seitenzahl": "aus Seite X von Y",
  "anzahl_uv": "Unterverteilungen",
  "maengel_anzahl": "Anzahl",
  "besondere_nutzung": []
}
NUR JSON.""",
    },
}

SAMPLE_SIZE = 200


def process_pdf(pdf_path: str, prompt: str, material: str, idx: int) -> dict:
    try:
        text = extract_text(pdf_path, maxpages=5)
        if len(text) < 100:
            return {"file": Path(pdf_path).name, "material": material, "error": "too_short"}

        text_truncated = text[:8000]

        msg = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=1000,
            messages=[{"role": "user", "content": f"Prüfbericht:\n\n{text_truncated}"}],
            system=prompt,
        )

        raw = msg.content[0].text.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]

        result = json.loads(raw)
        result["file"] = Path(pdf_path).name
        result["material"] = material
        result["input_tokens"] = msg.usage.input_tokens
        result["output_tokens"] = msg.usage.output_tokens
        return result

    except json.JSONDecodeError:
        return {"file": Path(pdf_path).name, "material": material, "error": "json_parse"}
    except Exception as e:
        return {"file": Path(pdf_path).name, "material": material, "error": str(e)[:100]}


def main():
    random.seed(42)
    all_results = []
    total_in = 0
    total_out = 0

    for material, config in MATERIALS.items():
        pdfs = list(config["path"].glob(config["pattern"]))
        if not pdfs:
            print(f"\n⚠ {material}: no PDFs found in {config['path']}")
            continue

        sample = random.sample(pdfs, min(SAMPLE_SIZE, len(pdfs)))
        print(f"\n{'='*70}")
        print(f"{material}: {len(sample)} / {len(pdfs)} PDFs")
        print(f"{'='*70}")

        results = []
        with ThreadPoolExecutor(max_workers=8) as executor:
            futures = {
                executor.submit(process_pdf, str(f), config["prompt"], material, i): i
                for i, f in enumerate(sample)
            }
            for future in as_completed(futures):
                r = future.result()
                results.append(r)
                total_in += r.get("input_tokens", 0)
                total_out += r.get("output_tokens", 0)

                i = len(results)
                if i % 50 == 0 or i == len(sample):
                    errors = sum(1 for x in results if "error" in x)
                    print(f"  {i}/{len(sample)} processed ({errors} errors)")

        all_results.extend(results)

        # Stats per material
        valid = [r for r in results if "error" not in r]
        errors = [r for r in results if "error" in r]
        print(f"  Valid: {len(valid)}, Errors: {len(errors)}")

        if valid:
            # Gebäudetyp distribution
            typen = {}
            for r in valid:
                t = r.get("gebaeudetyp", "?") or "?"
                typen[t] = typen.get(t, 0) + 1
            print(f"  Gebäudetypen:")
            for t, c in sorted(typen.items(), key=lambda x: -x[1])[:8]:
                print(f"    {t:25s} {c:4d} ({c/len(valid)*100:.0f}%)")

            # Key fill rates
            if material == "MA507":
                fields = ["gebaeudetyp", "prueftage", "seitenzahl", "anzahl_uv", "maengel_anzahl", "ist_gesamtanlage", "stockwerke_erkannt", "besondere_nutzung"]
            elif material == "MA560":
                fields = ["gebaeudetyp", "anzahl_gepruefte_geraete", "prueftage", "maengel_anzahl", "fehlerquote_prozent"]
            elif material == "MA510":
                fields = ["gebaeudetyp", "bundesland", "grundlage", "prueftage", "maengel_anzahl", "besondere_nutzung"]
            else:
                fields = ["gebaeudetyp", "prueftage", "maengel_anzahl", "anzahl_uv"]

            print(f"  Fill Rates:")
            for field in fields:
                filled = sum(1 for r in valid if r.get(field) not in [None, "null", "", False, [], 0])
                print(f"    {field:30s} {filled}/{len(valid)} ({filled/len(valid)*100:.0f}%)")

    # Save all
    output_path = "/tmp/batch_500er_preflight.json"
    with open(output_path, "w") as f:
        json.dump(all_results, f, indent=2, ensure_ascii=False)

    print(f"\n{'='*70}")
    print(f"TOTAL: {len(all_results)} PDFs, {total_in:,} input + {total_out:,} output tokens")
    print(f"Cost: ${total_in * 0.80 / 1e6 + total_out * 4.0 / 1e6:.2f}")
    print(f"Results: {output_path}")


if __name__ == "__main__":
    main()
