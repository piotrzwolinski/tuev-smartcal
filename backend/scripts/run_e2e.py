"""Standalone CLI runner for LLM-as-Judge E2E test suite.

Usage:
    cd backend
    ../venv/bin/python scripts/run_e2e.py                # all 50
    ../venv/bin/python scripts/run_e2e.py S01 S02 S03    # specific scenarios
    ../venv/bin/python scripts/run_e2e.py --category tricky  # by category
    ../venv/bin/python scripts/run_e2e.py --report results.json  # save report
"""

import argparse
import asyncio
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.e2e_scenarios import SCENARIOS, SCENARIO_MAP, E2EScenario
from scripts.e2e_judge import JudgeVerdict, JUDGE_DIMENSIONS


def _load_graph():
    try:
        from common.database import get_graph
        g = get_graph("dguv_v3")
        rows = g.query("MATCH (n) RETURN count(n) AS cnt").result_set
        if rows and rows[0][0] > 0:
            return
    except Exception:
        pass
    from products.dguv_v3.graph_schema import load_dguv_v3_graph
    load_dguv_v3_graph()


async def run_scenario(scenario: E2EScenario) -> JudgeVerdict:
    from products.dguv_v3.chat import (
        get_or_create_session,
        coordinator_respond,
        inject_kalkulation_result,
        coordinator_summarize,
    )
    from products.dguv_v3 import DGUV_V3 as gewerk
    from engine.graph_pricing_engine import GraphPricingEngine
    from scripts.e2e_judge import user_llm_generate, judge_evaluate

    session = get_or_create_session()
    conversation = []
    all_angebote = []
    all_provenance = []
    last_system_msg = ""

    for turn_idx in range(scenario.max_turns):
        user_msg = await user_llm_generate(
            scenario, conversation, turn_idx,
            system_response=last_system_msg,
        )
        if user_msg is None:
            break

        result = await coordinator_respond(session, user_msg)
        turn_record = {"turn": turn_idx, "user": user_msg, "coordinator": result}
        last_system_msg = result.get("message", "")

        if result.get("action") == "calculate":
            params = {k: v for k, v in result.get("params", {}).items() if v is not None}
            try:
                merkmale = gewerk.merkmale_schema(**params)
            except Exception as e:
                turn_record["validation_error"] = str(e)
                conversation.append(turn_record)
                continue

            graph_engine = GraphPricingEngine("dguv_v3")
            angebot_obj = graph_engine.calculate(gewerk, merkmale)
            provenance = graph_engine.provenance

            angebot = angebot_obj.to_dict()
            angebot["provenance"] = provenance
            all_angebote.append(angebot)
            all_provenance.extend(provenance)

            inject_kalkulation_result(session, angebot)
            summary = await coordinator_summarize(session)
            turn_record["angebot"] = angebot
            turn_record["summary"] = summary
            last_system_msg = summary.get("message", "")

        conversation.append(turn_record)

    verdict = await judge_evaluate(scenario, conversation, all_angebote, all_provenance)
    verdict._conversation = conversation
    verdict._angebote = all_angebote
    return verdict


async def main(scenarios: list[E2EScenario], report_path: str | None = None):
    print("Loading DGUV V3 graph...")
    _load_graph()
    print(f"Running {len(scenarios)} E2E scenarios...\n")

    results = []
    passed = 0
    failed = 0
    t0 = time.time()

    for i, scenario in enumerate(scenarios):
        t_start = time.time()
        print(f"[{i+1}/{len(scenarios)}] {scenario.id}: {scenario.name}...", end="", flush=True)

        try:
            verdict = await run_scenario(scenario)
        except Exception as e:
            verdict = JudgeVerdict(scenario_id=scenario.id, error=str(e))

        elapsed = time.time() - t_start
        status = "PASS" if verdict.passed else "FAIL"
        print(f" {status} ({verdict.avg_score:.1f}/5) [{elapsed:.1f}s]")

        if not verdict.passed:
            failed += 1
            for dim in JUDGE_DIMENSIONS:
                score = verdict.scores.get(dim, 0)
                if score < 3:
                    reason = verdict.reasoning.get(dim, "")
                    print(f"    ✗ {dim}: {score}/5 — {reason[:100]}")
            if verdict.error:
                print(f"    ERROR: {verdict.error}")
        else:
            passed += 1

        result_entry = verdict.to_dict()
        result_entry["name"] = scenario.name
        result_entry["category"] = scenario.category
        result_entry["elapsed_s"] = round(elapsed, 1)
        if hasattr(verdict, "_angebote") and verdict._angebote:
            last = verdict._angebote[-1]
            result_entry["total"] = last.get("total", 0)
            result_entry["confidence"] = last.get("confidence", 0)
        results.append(result_entry)

    elapsed_total = time.time() - t0

    print(f"\n{'═' * 70}")
    print(f"  RESULTS: {passed} passed, {failed} failed, {len(scenarios)} total")
    print(f"  Time: {elapsed_total:.0f}s ({elapsed_total/len(scenarios):.1f}s/scenario)")
    print(f"{'═' * 70}")

    by_cat = {}
    for r in results:
        cat = r.get("category", "?")
        by_cat.setdefault(cat, []).append(r)

    print(f"\n  {'Category':<15s} {'Pass':>5s} {'Fail':>5s} {'Avg':>6s}")
    print(f"  {'─' * 35}")
    for cat, items in sorted(by_cat.items()):
        cat_pass = sum(1 for r in items if r["passed"])
        cat_fail = len(items) - cat_pass
        cat_avg = sum(r["avg_score"] for r in items) / len(items)
        print(f"  {cat:<15s} {cat_pass:>5d} {cat_fail:>5d} {cat_avg:>5.1f}")

    dim_avgs = {}
    for dim in JUDGE_DIMENSIONS:
        vals = [r["scores"].get(dim, 0) for r in results if r["scores"]]
        dim_avgs[dim] = sum(vals) / len(vals) if vals else 0.0

    print(f"\n  {'Dimension':<15s} {'Avg':>6s}")
    print(f"  {'─' * 25}")
    for dim in JUDGE_DIMENSIONS:
        print(f"  {dim:<15s} {dim_avgs[dim]:>5.1f}")

    if report_path:
        report = {
            "total_scenarios": len(scenarios),
            "passed": passed,
            "failed": failed,
            "elapsed_s": round(elapsed_total, 1),
            "dimension_averages": {k: round(v, 2) for k, v in dim_avgs.items()},
            "results": results,
        }
        with open(report_path, "w") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        print(f"\n  Report saved to {report_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run DGUV V3 E2E LLM-as-Judge tests")
    parser.add_argument("scenarios", nargs="*", help="Scenario IDs (e.g. S01 S02)")
    parser.add_argument("--category", "-c", help="Run only scenarios in this category")
    parser.add_argument("--report", "-r", help="Save JSON report to this path")
    args = parser.parse_args()

    selected = SCENARIOS
    if args.scenarios:
        selected = [SCENARIO_MAP[sid] for sid in args.scenarios if sid in SCENARIO_MAP]
    elif args.category:
        selected = [s for s in SCENARIOS if s.category == args.category]

    if not selected:
        print("No matching scenarios found.")
        sys.exit(1)

    asyncio.run(main(selected, report_path=args.report))
