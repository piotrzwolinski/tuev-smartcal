#!/usr/bin/env python3
"""MA560-Sample-Extraktion (10%) — Merkmale (anzahl_gepruefte_geraete = BM) für
die Degression-Kalibrierung (P2). Reuse process_pdf + MA560_PROMPT aus dem
Hauptbatch. Output: ~/Desktop/TUEV/_extracted/batch_MA560_sample_results.json.

Lauf: ./venv/bin/python scripts/batch_ma560_sample.py [PCT]   (default 0.10)
"""
import json
import random
import sys
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

sys.path.insert(0, str(Path(__file__).parent))
from batch_500er_full import process_pdf, MA560_PROMPT  # noqa: E402

PCT = float(sys.argv[1]) if len(sys.argv) > 1 else 0.10
SRC = Path.home() / "Desktop/TUEV/560 (1)"
OUT = Path.home() / "Desktop/TUEV/_extracted/batch_MA560_sample_results.json"

pdfs = sorted(SRC.glob("*MA560*.pdf"))
random.seed(42)
sample = random.sample(pdfs, int(len(pdfs) * PCT))
print(f"MA560: {len(pdfs)} total → Sample {len(sample)} ({PCT:.0%}), workers=32")

results = []
with ThreadPoolExecutor(max_workers=32) as ex:
    futs = {ex.submit(process_pdf, str(f), MA560_PROMPT, "MA560"): f for f in sample}
    for i, fut in enumerate(as_completed(futs), 1):
        try:
            results.append(fut.result())
        except Exception as e:
            results.append({"error": str(e)[:80]})
        if i % 50 == 0:
            print(f"  {i}/{len(sample)}")
            json.dump(results, open(OUT, "w"), ensure_ascii=False)

json.dump(results, open(OUT, "w"), ensure_ascii=False)
ok = sum(1 for r in results if isinstance(r, dict) and not r.get("error"))
print(f"FERTIG: {len(results)} verarbeitet, {ok} OK → {OUT}")
