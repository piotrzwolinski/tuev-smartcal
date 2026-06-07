"""DGUV V3 Preflight: 50 random PDFs → open-ended LLM extraction → understand data quality."""

import json
import os
import sys
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

from pdfminer.high_level import extract_text
import anthropic

client = anthropic.Anthropic()

PREFLIGHT_PROMPT = """Du analysierst einen TÜV SÜD Prüfbericht für eine DGUV V3 Prüfung (ortsfeste elektrische Anlage).

Extrahiere ALLES was du finden kannst. Sei ehrlich — wenn etwas nicht im Bericht steht, schreib null.

{
  "gebaeudetyp": "Was für ein Gebäude? (Schule, Büro, Industrie, Hotel, Krankenhaus, Supermarkt, Kirche, Tiefgarage, Versammlungsstätte, Wohngebäude, Autohaus, ... oder null wenn unklar)",
  "gebaeudetyp_quelle": "Woher weißt du das? (Standortname, Gegenstand, Technische Beschreibung, oder 'unklar')",
  "standort_ort": "Stadt/Ort",
  "standort_plz": "PLZ",
  "betreiber": "Wer ist der Betreiber/Auftraggeber?",
  "betreiber_typ": "Typ des Betreibers (Kommune, Firma, Wohnungseigentümer, Kirche, ...)",
  "gegenstand": "Was genau wurde geprüft? (ganze Anlage, Teilanlage, einzelne Maschine, ...)",
  "ist_gesamtanlage": true/false,
  "pruefdauer_tage": "Anzahl Prüftage (aus Zeitraum der Prüfung ableitbar)",
  "seitenzahl": "Geschätzte Seitenanzahl des Berichts",
  "verteilungen_gefunden": true/false,
  "anzahl_uv": "Anzahl Unterverteilungen (null wenn nicht erkennbar)",
  "anzahl_hv": "Anzahl Hauptverteilungen (null wenn nicht erkennbar)",
  "anzahl_nshv": "Anzahl NSHV (null wenn nicht erkennbar)",
  "rcd_fi_count": "Anzahl gemessener RCD/FI Schalter (null wenn nicht erkennbar)",
  "flaeche_m2": "Fläche in m² (null wenn nicht angegeben — ist selten vorhanden!)",
  "stockwerke": "Anzahl Stockwerke (null wenn nicht erkennbar, z.B. aus KG/EG/OG/DG)",
  "raeume_erwähnt": ["Liste der erwähnten Räume/Bereiche aus Mängeltabelle oder Text"],
  "maengel_anzahl": "Anzahl Mängel",
  "maengel_schwere": "keine / geringfügig / erheblich / gefährlich",
  "grundlage": "Baurecht oder Kundenauftrag?",
  "baurecht_vorhanden": true/false,
  "besondere_merkmale": ["Alles Auffällige: Zuschauerzahl, Stellplätze, Kassenanzahl, Maschinentyp, etc."],
  "nutzbar_fuer_kalkulation": "gut / mittel / schlecht — deine Einschätzung ob man aus diesem Bericht Rückschlüsse auf Aufwand ziehen kann",
  "begruendung_nutzbarkeit": "Warum gut/mittel/schlecht?"
}

Gib NUR valides JSON zurück. Keine Erklärungen."""


def process_pdf(pdf_path: str, idx: int) -> dict:
    try:
        text = extract_text(pdf_path, maxpages=5)
        if len(text) < 100:
            return {"file": Path(pdf_path).name, "error": "too_short", "text_len": len(text)}

        # Truncate to ~8000 chars to keep tokens reasonable
        text_truncated = text[:8000]

        msg = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=1500,
            messages=[{"role": "user", "content": f"Prüfbericht:\n\n{text_truncated}"}],
            system=PREFLIGHT_PROMPT,
        )

        raw = msg.content[0].text.strip()
        # Parse JSON
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]

        result = json.loads(raw)
        result["file"] = Path(pdf_path).name
        result["text_len"] = len(text)
        result["input_tokens"] = msg.usage.input_tokens
        result["output_tokens"] = msg.usage.output_tokens
        print(f"  {idx+1:2d}. {Path(pdf_path).name[:45]:45s} | {result.get('gebaeudetyp', '?'):20s} | {result.get('nutzbar_fuer_kalkulation', '?')}")
        return result

    except json.JSONDecodeError as e:
        print(f"  {idx+1:2d}. {Path(pdf_path).name[:45]:45s} | JSON ERROR: {e}")
        return {"file": Path(pdf_path).name, "error": "json_parse", "raw": raw[:200] if 'raw' in dir() else ""}
    except Exception as e:
        print(f"  {idx+1:2d}. {Path(pdf_path).name[:45]:45s} | ERROR: {e}")
        return {"file": Path(pdf_path).name, "error": str(e)}


def main():
    with open("/tmp/dguv_preflight_files.json") as f:
        files = json.load(f)

    print(f"DGUV V3 Preflight: {len(files)} PDFs")
    print("=" * 90)

    results = []
    total_input = 0
    total_output = 0

    # Sequential for now (Haiku is fast enough)
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = {executor.submit(process_pdf, f, i): i for i, f in enumerate(files)}
        for future in as_completed(futures):
            result = future.result()
            results.append(result)
            total_input += result.get("input_tokens", 0)
            total_output += result.get("output_tokens", 0)

    # Save results
    output_path = "/tmp/dguv_preflight_results.json"
    with open(output_path, "w") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    # Summary
    print("\n" + "=" * 90)
    print(f"Total: {len(results)} PDFs processed")
    print(f"Tokens: {total_input:,} input + {total_output:,} output")
    print(f"Est. cost: ${total_input * 0.80 / 1_000_000 + total_output * 4.0 / 1_000_000:.2f}")

    errors = [r for r in results if "error" in r]
    print(f"Errors: {len(errors)}")

    # Gebäudetyp distribution
    typen = {}
    for r in results:
        if "error" not in r:
            t = r.get("gebaeudetyp", "unklar") or "unklar"
            typen[t] = typen.get(t, 0) + 1
    print(f"\nGebäudetyp-Verteilung:")
    for t, c in sorted(typen.items(), key=lambda x: -x[1]):
        print(f"  {t:30s} {c:3d} ({c/len(results)*100:.0f}%)")

    # Nutzbarkeit
    nutz = {}
    for r in results:
        if "error" not in r:
            n = r.get("nutzbar_fuer_kalkulation", "?") or "?"
            nutz[n] = nutz.get(n, 0) + 1
    print(f"\nNutzbarkeit für Kalkulation:")
    for n, c in sorted(nutz.items(), key=lambda x: -x[1]):
        print(f"  {n:10s} {c:3d} ({c/len(results)*100:.0f}%)")

    # Fill rates
    fields = ["gebaeudetyp", "standort_ort", "betreiber", "verteilungen_gefunden",
              "anzahl_uv", "flaeche_m2", "stockwerke", "pruefdauer_tage", "rcd_fi_count",
              "maengel_anzahl", "grundlage"]
    print(f"\nFill Rates:")
    valid = [r for r in results if "error" not in r]
    for field in fields:
        filled = sum(1 for r in valid if r.get(field) is not None and r.get(field) != "null" and r.get(field) != "" and r.get(field) != False)
        print(f"  {field:30s} {filled:3d}/{len(valid)} ({filled/max(len(valid),1)*100:.0f}%)")

    print(f"\nResults saved to {output_path}")


if __name__ == "__main__":
    main()
