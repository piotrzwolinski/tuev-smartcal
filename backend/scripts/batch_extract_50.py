"""Batch extraction v2: 50 MA570 PDFów → anonimizer → Haiku → normalize → Pydantic → retry Sonnet.

Pipeline:
  1. pdfminer extract text
  2. anonymizer (type-preserving)
  3. Haiku extraction → JSON
  4. Normalize (common/normalize.py: enum mapping)
  5. Pydantic BlitzschutzMerkmale validation
  6. Jeśli fail → Sonnet retry z lepszym promptem
"""

import json
import os
import random
import sys
import time
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

# Load env
env_path = Path(__file__).parent.parent / ".env"
if env_path.exists():
    for line in env_path.read_text().splitlines():
        if "=" in line and not line.startswith("#"):
            k, v = line.split("=", 1)
            os.environ[k.strip()] = v.strip()

sys.path.insert(0, str(Path(__file__).parent.parent))

from pdfminer.high_level import extract_text
import anthropic
from pydantic import ValidationError

from common.anonymizer import anonymize_pdf_text
from common.normalize import normalize_blitzschutz_extracted
from products.blitzschutz import BLITZSCHUTZ


MA570_DIR = Path.home() / "Desktop" / "TUEV" / "570_572_574"
OUT_DIR = Path.home() / "Desktop" / "TUEV" / "_analysis"
OUT_DIR.mkdir(parents=True, exist_ok=True)


def _parse_json(text: str):
    cleaned = text.strip()
    if "```json" in cleaned:
        cleaned = cleaned.split("```json")[1].split("```")[0].strip()
    elif "```" in cleaned:
        cleaned = cleaned.split("```")[1].split("```")[0].strip()
    return json.loads(cleaned)


def llm_extract(client, anon_text: str, prompt: str, model: str, hint: str = None):
    """Call LLM z optional hint dla retry."""
    user_content = (
        "Extrahiere Merkmale aus diesem anonymisierten TÜV Prüfbericht. "
        "Pseudonyme wie <SCHULE_xxx>, <KRANKENHAUS_xxx>, <CITY_xxx> "
        "enthalten die Kategorie des Gebäudes/Standorts — nutze sie für `nutzung`.\n\n"
    )
    if hint:
        user_content += f"**Retry-Hinweis**: {hint}\n\n"
    user_content += anon_text

    msg = client.messages.create(
        model=model,
        max_tokens=2048,
        system=prompt,
        messages=[{"role": "user", "content": user_content}],
    )
    return msg


def extract_one(pdf_path: Path, client: anthropic.Anthropic, prompt: str):
    try:
        raw = extract_text(str(pdf_path))
    except Exception as e:
        return {"file": pdf_path.name, "error": f"pdfminer: {e}"}

    if len(raw) < 200:
        return {"file": pdf_path.name, "error": f"too_short"}

    anon = anonymize_pdf_text(raw)
    input_tokens = 0
    output_tokens = 0

    # ─── Haiku first pass ───
    try:
        msg = llm_extract(client, anon.anonymized_text, prompt, "claude-haiku-4-5-20251001")
        input_tokens += msg.usage.input_tokens
        output_tokens += msg.usage.output_tokens
        raw_extract = _parse_json(msg.content[0].text)
    except json.JSONDecodeError:
        return {"file": pdf_path.name, "error": "json_parse_failed_haiku",
                "input_tokens": input_tokens, "output_tokens": output_tokens}
    except Exception as e:
        return {"file": pdf_path.name, "error": f"haiku: {e}",
                "input_tokens": input_tokens, "output_tokens": output_tokens}

    # ─── Normalize ───
    normalized = normalize_blitzschutz_extracted(raw_extract)

    # ─── Pydantic validation ───
    validation_attempt = "haiku_norm"
    try:
        merkmale = BLITZSCHUTZ.merkmale_schema(**normalized)
        schema_valid = True
        schema_errors = None
    except ValidationError as e:
        schema_valid = False
        schema_errors = str(e)[:300]

        # ─── Sonnet retry ───
        validation_attempt = "sonnet_retry"
        try:
            # Build hint z errors
            error_fields = [err["loc"][0] for err in e.errors()]
            hint = f"Vorherige Extraktion versagte bei: {', '.join(set(map(str, error_fields)))}. Bitte extra genau diese Felder prüfen."

            msg2 = llm_extract(client, anon.anonymized_text, prompt, "claude-sonnet-4-5-20250929", hint=hint)
            input_tokens += msg2.usage.input_tokens
            output_tokens += msg2.usage.output_tokens
            raw_extract2 = _parse_json(msg2.content[0].text)
            normalized = normalize_blitzschutz_extracted(raw_extract2)

            # Try Pydantic again
            merkmale = BLITZSCHUTZ.merkmale_schema(**normalized)
            schema_valid = True
            schema_errors = None
        except Exception as e2:
            schema_errors = f"Haiku+Sonnet failed: {str(e2)[:200]}"

    return {
        "file": pdf_path.name,
        "raw_haiku": raw_extract,
        "normalized": normalized,
        "schema_valid": schema_valid,
        "schema_errors": schema_errors,
        "validation_attempt": validation_attempt,
        "pii_masked": sum(anon.categories.values()),
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
    }


def main():
    random.seed(42)
    all_pdfs = list(MA570_DIR.glob("*MA570-WP.pdf"))
    sample = random.sample(all_pdfs, min(50, len(all_pdfs)))
    print(f"Pool: {len(all_pdfs)}, Sampled: {len(sample)}\n")

    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    prompt = BLITZSCHUTZ.extraction_prompt()

    results = []
    t0 = time.time()

    with ThreadPoolExecutor(max_workers=5) as pool:
        futures = {pool.submit(extract_one, pdf, client, prompt): pdf for pdf in sample}
        for i, fut in enumerate(as_completed(futures), 1):
            res = fut.result()
            results.append(res)
            elapsed = time.time() - t0
            status = "✓" if res.get("schema_valid") else "⚠" if "error" not in res else "✗"
            attempt = res.get("validation_attempt", "error")
            print(f"  [{i:>2}/{len(sample)}] {status} {attempt:<14} {res['file'][:45]:<45}  t={elapsed:.0f}s", flush=True)

    # ─── Summary ───
    print(f"\n=== BATCH COMPLETE w {time.time() - t0:.0f}s ===")
    ok = [r for r in results if "error" not in r]
    err = [r for r in results if "error" in r]
    schema_ok = [r for r in ok if r.get("schema_valid")]
    haiku_only = [r for r in schema_ok if r.get("validation_attempt") == "haiku_norm"]
    sonnet_retry = [r for r in schema_ok if r.get("validation_attempt") == "sonnet_retry"]

    print(f"  Total success: {len(ok)}/{len(results)} ({len(ok)/len(results):.0%})")
    print(f"  Schema valid:  {len(schema_ok)}/{len(ok)} ({len(schema_ok)/max(len(ok),1):.0%})")
    print(f"    Haiku + normalize:  {len(haiku_only)}/{len(ok)} ({len(haiku_only)/max(len(ok),1):.0%})")
    print(f"    Sonnet retry saved: {len(sonnet_retry)}")
    print(f"  Errors: {len(err)}")

    # Fill rates (na schema-valid)
    print(f"\n=== FILL RATE per pole (na {len(schema_ok)} schema-valid) ===")
    field_fill = {}
    for r in schema_ok:
        for k, v in r["normalized"].items():
            if k not in field_fill:
                field_fill[k] = {"filled": 0, "null": 0}
            if v is None:
                field_fill[k]["null"] += 1
            else:
                field_fill[k]["filled"] += 1

    for field, stats in sorted(field_fill.items(), key=lambda x: -x[1]["filled"]):
        total = stats["filled"] + stats["null"]
        pct = stats["filled"] / total * 100 if total else 0
        bar = "█" * int(pct / 5) + "·" * (20 - int(pct / 5))
        print(f"  {field:<35} {bar} {pct:3.0f}%  ({stats['filled']}/{total})")

    # Koszt
    total_in = sum(r.get("input_tokens", 0) for r in results)
    total_out = sum(r.get("output_tokens", 0) for r in results)
    # Haiku: $1/$5 per 1M, Sonnet: $3/$15 per 1M  (averaging → approximation)
    haiku_only_cost_est = (202_954 * 1.0 + 14_896 * 5.0) / 1_000_000  # z poprzedniego runu
    cost = total_in * 1.0 / 1_000_000 + total_out * 5.0 / 1_000_000  # lower bound Haiku-only
    sonnet_cost = len(sonnet_retry) * 0.025  # ~$0.025 per Sonnet retry (rough)
    total_cost_est = cost + sonnet_cost
    print(f"\n=== KOSZT ===")
    print(f"  Tokens: {total_in:,} input + {total_out:,} output")
    print(f"  Haiku-only cost: ${cost:.3f}")
    print(f"  + Sonnet retries ({len(sonnet_retry)}): ~${sonnet_cost:.3f}")
    print(f"  Total: ~${total_cost_est:.3f}")
    print(f"  Extrapolated 5,403 MA570: ~${total_cost_est * 5403 / len(results):.0f}")

    # Save
    out_path = OUT_DIR / "batch50_v2_results.json"
    out_path.write_text(json.dumps(results, indent=2, ensure_ascii=False))
    print(f"\n✓ Saved: {out_path}")


if __name__ == "__main__":
    main()
