"""Batch extraction MA505 VdS with Branchen-Pflichtfeld discovery."""

import json
import os
import time
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

from pdfminer.high_level import extract_text
import anthropic

client = anthropic.Anthropic()

MA505_PROMPT = """Du analysierst einen TÜV SÜD Prüfbericht VdS 2871 ortsfeste elektrische Anlage (MA505).

WICHTIG: In MA505 Berichten gibt es ein Pflichtfeld "Art des Betriebes oder der Anlage" mit einem Branchen-Code (z.B. 0001-Bürogebäude, 0902-Hotel, 0904-Kaufhaus). Extrahiere diesen Code und die Beschreibung.

{
  "branchen_code": "4-stelliger Code z.B. 0001, 0902, 0904",
  "branchen_bezeichnung": "Text z.B. Bürogebäude Immobilienverwaltung, Hotel- und Gaststättenbetriebe",
  "gebaeudetyp": "Freitext",
  "standort_plz": "PLZ",
  "standort_ort": "Stadt",
  "betreiber_branche": "Freitext",
  "prueftage": Anzahl,
  "seitenzahl": Anzahl,
  "anzahl_uv": Anzahl,
  "anzahl_hv": Anzahl,
  "maengel_anzahl": Anzahl,
  "maengel_max_schwere": "keine oder geringfuegig oder erheblich oder gefaehrlich",
  "_discovery": {
    "raeume_typen": {},
    "erwaehnte_anlagen": [],
    "dokumentation_zustand": "vorhanden_vollstaendig oder vorhanden_unvollstaendig oder nicht_vorhanden",
    "baujahr_oder_alter": "Jahr",
    "auffaelligkeiten": []
  }
}

NUR valides JSON."""

WORKERS = 32
RATE_LIMIT_DELAY = 0.1
OUTPUT_PATH = "/tmp/batch_MA505_results.json"


def process_pdf(pdf_path: str) -> dict:
    try:
        text = extract_text(pdf_path, maxpages=6)
        if len(text) < 100:
            return {"file": Path(pdf_path).name, "material": "MA505", "error": "too_short"}

        time.sleep(RATE_LIMIT_DELAY)

        msg = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=1000,
            messages=[{"role": "user", "content": f"Pruefbericht:\n\n{text[:10000]}"}],
            system=MA505_PROMPT,
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
        result["material"] = "MA505"
        result["input_tokens"] = msg.usage.input_tokens
        result["output_tokens"] = msg.usage.output_tokens
        return result

    except json.JSONDecodeError:
        return {"file": Path(pdf_path).name, "material": "MA505", "error": "json_parse"}
    except anthropic.RateLimitError:
        time.sleep(5)
        return {"file": Path(pdf_path).name, "material": "MA505", "error": "rate_limit"}
    except Exception as e:
        return {"file": Path(pdf_path).name, "material": "MA505", "error": str(e)[:100]}


MAX_SAMPLE = 8000  # Budget limit: ~$56 at $0.007/PDF


def main():
    pdf_dir = Path.home() / "Desktop/TUEV/505"
    pdfs = sorted(pdf_dir.glob("*MA505*.pdf"))
    print(f"MA505 VdS: {len(pdfs)} total PDFs")

    if len(pdfs) > MAX_SAMPLE:
        import random
        random.seed(42)
        pdfs = random.sample(pdfs, MAX_SAMPLE)
        print(f"  Sampled {MAX_SAMPLE} (budget limit)")

    print(f"  Processing {len(pdfs)} PDFs (workers={WORKERS})")

    # Resume support
    existing = {}
    if Path(OUTPUT_PATH).exists():
        with open(OUTPUT_PATH) as f:
            for r in json.load(f):
                existing[r.get("file", "")] = r
        print(f"  Resuming: {len(existing)} already processed")

    pdfs_to_process = [f for f in pdfs if f.name not in existing]
    results = list(existing.values())
    print(f"  Remaining: {len(pdfs_to_process)}")

    if not pdfs_to_process:
        print("  Already complete!")
        return

    start = time.time()
    total_in = sum(r.get("input_tokens", 0) for r in results)
    total_out = sum(r.get("output_tokens", 0) for r in results)
    last_status = time.time()
    last_save = time.time()
    new_count = 0

    with ThreadPoolExecutor(max_workers=WORKERS) as executor:
        futures = {executor.submit(process_pdf, str(f)): f for f in pdfs_to_process}
        for future in as_completed(futures):
            r = future.result()
            results.append(r)
            new_count += 1
            total_in += r.get("input_tokens", 0)
            total_out += r.get("output_tokens", 0)

            now = time.time()

            if new_count % 100 == 0 or now - last_save > 120:
                last_save = now
                with open(OUTPUT_PATH, "w") as f:
                    json.dump(results, f, ensure_ascii=False)

            if now - last_status >= 30 or len(results) == len(pdfs):
                last_status = now
                elapsed = now - start
                rate = new_count / elapsed * 60 if elapsed > 0 else 0
                errors = sum(1 for x in results if "error" in x)
                remaining = len(pdfs) - len(results)
                eta = remaining / (rate / 60) / 60 if rate > 0 else 0
                cost = total_in * 0.80 / 1e6 + total_out * 4.0 / 1e6
                print(f"  {len(results):6d}/{len(pdfs)} ({len(results)/len(pdfs)*100:.0f}%) | {rate:.0f}/min | err:{errors} | {elapsed/60:.1f}min | ETA:{eta:.0f}min | ${cost:.2f}", flush=True)

    # Final save
    with open(OUTPUT_PATH, "w") as f:
        json.dump(results, f, ensure_ascii=False)

    valid = [r for r in results if "error" not in r]
    errors_list = [r for r in results if "error" in r]
    elapsed = time.time() - start
    cost = total_in * 0.80 / 1e6 + total_out * 4.0 / 1e6

    print(f"\nDONE: {len(valid)} valid, {len(errors_list)} errors in {elapsed/60:.0f} min | ${cost:.2f}")

    # Branchen-Code stats
    from collections import Counter
    codes = Counter()
    for r in valid:
        code = r.get("branchen_code")
        bez = r.get("branchen_bezeichnung", "?")
        if code:
            codes[f"{code}-{bez[:30]}"] += 1
    print("\nBranchen-Codes:")
    for code, count in codes.most_common(15):
        print(f"  {code:40s} {count:5d} ({count/len(valid)*100:.1f}%)")


if __name__ == "__main__":
    main()
