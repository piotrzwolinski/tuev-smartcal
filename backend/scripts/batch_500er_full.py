"""Full batch extraction: ALL 500er PDFs with discovery prompt."""

import json
import os
import random
import sys
import time
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

from pdfminer.high_level import extract_text
import anthropic

client = anthropic.Anthropic()

DISCOVERY_PROMPT = """Du analysierst einen TÜV SÜD Prüfbericht. Extrahiere ALLES was du finden kannst.

{
  "ist_gesamtanlage": true oder false,
  "gebaeudetyp": "Freitext",
  "standort_plz": "PLZ",
  "standort_ort": "Stadt",
  "betreiber_typ": "Kommune oder Firma oder Kirche oder Wohnungseigentuemer oder sonstige",
  "betreiber_branche": "Freitext z.B. Lebensmittelhandel, Automobilzulieferer, Bildungseinrichtung, Finanzdienstleistungen",
  "prueftage": Anzahl Prueftage aus Zeitraum berechnen,
  "seitenzahl": Anzahl aus letztem Seite X von Y,
  "anzahl_uv": Anzahl Unterverteilungen,
  "anzahl_hv": Anzahl Hauptverteilungen,
  "anzahl_rcd_messwerte": Anzahl RCD/FI Messzeilen,
  "stockwerke_erkannt": ["KG","EG","1.OG"],
  "maengel_anzahl": Anzahl,
  "maengel_max_schwere": "keine oder geringfuegig oder erheblich oder gefaehrlich",
  "grundlage_baurecht": true oder false,
  "nea_vorhanden": true oder false,
  "besondere_ausstattung": ["Aufzug","Turnhalle","Labor","Kueche"],
  "_discovery": {
    "raeume_typen": {"Buero": 3, "Labor": 2, "Kueche": 1, "Flur": 5},
    "erwaehnte_anlagen": ["Aufzug", "Brandmeldeanlage", "PV-Anlage", "Ladestation", "Sicherheitsbeleuchtung", "Klimaanlage", "USV", "Kran"],
    "erwaehnte_normen": ["DIN VDE 0100-710"],
    "messungen_anzahl_zeilen": Anzahl Zeilen in Messtabelle,
    "dokumentation_zustand": "vorhanden_vollstaendig oder vorhanden_unvollstaendig oder nicht_vorhanden oder nicht_erwaehnt",
    "vorheriger_pruefbericht": true oder false,
    "gebaeude_komplex_teile": Anzahl Gebaeudeteile wenn mehrere,
    "baujahr_oder_alter": "Jahr oder Beschreibung",
    "erschwernisse": ["laufender Betrieb", "Zugang eingeschraenkt", "Hoehenarbeit", "Ex-Zone"],
    "nicht_geprueft_bereiche": Anzahl Bereiche die nicht geprueft werden konnten,
    "anlagen_komplexitaet": Anzahl verschiedener Anlagentypen,
    "auffaelligkeiten": ["Freitext - alles was Aufwand beeinflusst"]
  }
}

NUR valides JSON. Keine Erklaerungen."""

MA560_PROMPT = """Du analysierst einen TÜV SÜD Prüfbericht DGUV V3 ortsveraenderliche Betriebsmittel (MA560).

{
  "gebaeudetyp": "Freitext",
  "gebaeudetyp_freitext": "exakter Text aus Bericht",
  "standort_plz": "PLZ",
  "standort_ort": "Stadt",
  "betreiber_typ": "Kommune oder Firma oder sonstige",
  "betreiber_branche": "Freitext",
  "anzahl_gepruefte_geraete": Anzahl,
  "davon_fehlerhaft": Anzahl,
  "fehlerquote_prozent": Prozent,
  "prueftage": Anzahl,
  "seitenzahl": Anzahl,
  "maengel_anzahl": Anzahl
}

NUR valides JSON."""

MA510_PROMPT = """Du analysierst einen TÜV SÜD Prüfbericht Baurecht elektrische Anlage (MA510).

{
  "gebaeudetyp": "Freitext",
  "standort_plz": "PLZ",
  "standort_ort": "Stadt",
  "betreiber_branche": "Freitext",
  "bundesland": "aus Landesbauordnung ableiten",
  "grundlage": "welche Verordnung",
  "prueftage": Anzahl,
  "seitenzahl": Anzahl,
  "anzahl_uv": Anzahl,
  "maengel_anzahl": Anzahl,
  "maengel_max_schwere": "keine oder geringfuegig oder erheblich oder gefaehrlich",
  "besondere_nutzung": ["Sicherheitsbeleuchtung","Brandmeldeanlage","RWA"],
  "_discovery": {
    "erwaehnte_anlagen": [],
    "dokumentation_zustand": "vorhanden_vollstaendig oder vorhanden_unvollstaendig oder nicht_vorhanden",
    "auffaelligkeiten": []
  }
}

NUR valides JSON."""

MA501_PROMPT = """Du analysierst einen TÜV SÜD Prüfbericht freiwirtschaftliche Pruefung elektrische Anlage (MA501).

{
  "gebaeudetyp": "Freitext",
  "standort_plz": "PLZ",
  "standort_ort": "Stadt",
  "betreiber_branche": "Freitext",
  "prueftage": Anzahl,
  "seitenzahl": Anzahl,
  "anzahl_uv": Anzahl,
  "maengel_anzahl": Anzahl,
  "maengel_max_schwere": "keine oder geringfuegig oder erheblich oder gefaehrlich",
  "_discovery": {
    "raeume_typen": {},
    "erwaehnte_anlagen": [],
    "dokumentation_zustand": "vorhanden_vollstaendig oder vorhanden_unvollstaendig oder nicht_vorhanden",
    "betreiber_branche_detail": "Freitext",
    "auffaelligkeiten": []
  }
}

NUR valides JSON."""

MATERIALS = {
    "MA507": {"path": Path.home() / "Desktop/TUEV/507", "pattern": "*MA507*.pdf", "prompt": DISCOVERY_PROMPT},
    # Veit 30.05: nur ortsfest (507+505) für 08.06
    # "MA560": {"path": Path.home() / "Desktop/TUEV/560 (1)", "pattern": "*MA560*.pdf", "prompt": MA560_PROMPT},
    # "MA510": {"path": Path.home() / "Desktop/TUEV/510", "pattern": "*MA510*.pdf", "prompt": MA510_PROMPT},
    # "MA501": {"path": Path.home() / "Desktop/TUEV/501", "pattern": "*MA501*.pdf", "prompt": MA501_PROMPT, "max_sample": 2000},
}

WORKERS = 32
RATE_LIMIT_DELAY = 0.1


def process_pdf(pdf_path: str, prompt: str, material: str) -> dict:
    try:
        text = extract_text(pdf_path, maxpages=6)
        if len(text) < 100:
            return {"file": Path(pdf_path).name, "material": material, "error": "too_short"}

        time.sleep(RATE_LIMIT_DELAY)

        msg = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=1500,
            messages=[{"role": "user", "content": f"Pruefbericht:\n\n{text[:10000]}"}],
            system=prompt,
        )

        raw = msg.content[0].text.strip()
        if "```" in raw:
            parts = raw.split("```")
            if len(parts) >= 2:
                raw = parts[1]
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
    except anthropic.RateLimitError:
        time.sleep(5)
        return {"file": Path(pdf_path).name, "material": material, "error": "rate_limit"}
    except Exception as e:
        return {"file": Path(pdf_path).name, "material": material, "error": str(e)[:100]}


def main():
    all_results = []
    total_in = 0
    total_out = 0
    start_time = time.time()

    for material, config in MATERIALS.items():
        pdfs = sorted(config["path"].glob(config["pattern"]))
        if not pdfs:
            print(f"\n⚠ {material}: no PDFs found")
            continue

        print(f"\n{'='*70}")
        print(f"{material}: {len(pdfs)} PDFs (workers={WORKERS})")
        print(f"{'='*70}")

        mat_start = time.time()
        data_dir = Path.home() / "Desktop/TUEV/_extracted"
        data_dir.mkdir(exist_ok=True)
        output_path = str(data_dir / f"batch_{material}_results.json")

        # Load existing results (resume support)
        existing = {}
        if Path(output_path).exists():
            with open(output_path) as f:
                for r in json.load(f):
                    existing[r.get("file", "")] = r
            print(f"  Resuming: {len(existing)} already processed")

        pdfs_to_process = [f for f in pdfs if f.name not in existing]
        results = list(existing.values())
        print(f"  Remaining: {len(pdfs_to_process)} to process")

        if not pdfs_to_process:
            print(f"  ✓ Already complete")
            all_results.extend(results)
            continue

        last_status = time.time()
        last_save = time.time()
        new_count = 0

        with ThreadPoolExecutor(max_workers=WORKERS) as executor:
            futures = {
                executor.submit(process_pdf, str(f), config["prompt"], material): f
                for f in pdfs_to_process
            }
            for future in as_completed(futures):
                r = future.result()
                results.append(r)
                new_count += 1
                total_in += r.get("input_tokens", 0)
                total_out += r.get("output_tokens", 0)

                now = time.time()
                i = len(results)

                # Save every 100 new results
                if new_count % 100 == 0 or now - last_save > 120:
                    last_save = now
                    with open(output_path, "w") as f:
                        json.dump(results, f, ensure_ascii=False)

                if now - last_status >= 30 or i == len(pdfs):
                    last_status = now
                    elapsed = now - mat_start
                    rate = new_count / elapsed * 60 if elapsed > 0 else 0
                    errors = sum(1 for x in results if "error" in x)
                    eta_min = (len(pdfs) - i) / (rate / 60) / 60 if rate > 0 else 0
                    cost_so_far = total_in * 0.80 / 1e6 + total_out * 4.0 / 1e6
                    print(f"  {i:6d}/{len(pdfs)} ({i/len(pdfs)*100:.0f}%) | {rate:.0f}/min | err:{errors} | {elapsed/60:.1f}min | ETA:{eta_min:.0f}min | ${cost_so_far:.2f}", flush=True)

        all_results.extend(results)

        # Final save
        with open(output_path, "w") as f:
            json.dump(results, f, ensure_ascii=False)

        valid = [r for r in results if "error" not in r]
        errors = [r for r in results if "error" in r]
        print(f"  ✓ {len(valid)} valid, ✗ {len(errors)} errors ({time.time()-mat_start:.0f}s)")
        print(f"  → {output_path}")

    data_dir = Path.home() / "Desktop/TUEV/_extracted"
    data_dir.mkdir(exist_ok=True)
    output_path = str(data_dir / "batch_500er_full_results.json")
    with open(output_path, "w") as f:
        json.dump(all_results, f, ensure_ascii=False)

    elapsed = time.time() - start_time
    cost = total_in * 0.80 / 1e6 + total_out * 4.0 / 1e6
    errors = sum(1 for r in all_results if "error" in r)

    print(f"\n{'='*70}")
    print(f"DONE: {len(all_results)} PDFs in {elapsed/60:.0f} min")
    print(f"Valid: {len(all_results)-errors}, Errors: {errors}")
    print(f"Tokens: {total_in:,} in + {total_out:,} out")
    print(f"Cost: ${cost:.2f}")
    print(f"Results: {output_path}")


if __name__ == "__main__":
    main()
