"""LLM-as-Judge E2E test suite — 50 multiturn DGUV V3 scenarios.

Runs each scenario in-process (no HTTP):
  1. User-LLM (Haiku) generates realistic customer messages from persona
  2. coordinator_respond() extracts merkmale
  3. GraphPricingEngine calculates with full provenance
  4. Judge-LLM (Haiku) scores 6 dimensions (0-5 each)

Usage:
    ./venv/bin/python -m pytest tests/test_e2e_llm_judge.py -v -x --tb=short
    ./venv/bin/python -m pytest tests/test_e2e_llm_judge.py -k "S01" -v
    ./venv/bin/python -m pytest tests/test_e2e_llm_judge.py -m "not slow" -v
"""

import asyncio
import json
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.e2e_scenarios import SCENARIOS, E2EScenario
from scripts.e2e_judge import (
    user_llm_generate,
    judge_evaluate,
    JudgeVerdict,
    JUDGE_DIMENSIONS,
)


def _ensure_graph_loaded():
    """Load DGUV V3 graph if not already loaded."""
    try:
        from common.database import get_graph
        g = get_graph("dguv_v3")
        rows = g.query("MATCH (n) RETURN count(n) AS cnt").result_set
        if rows and rows[0][0] > 0:
            return True
    except Exception:
        pass
    try:
        from products.dguv_v3.graph_schema import load_dguv_v3_graph
        load_dguv_v3_graph()
        return True
    except Exception as e:
        pytest.skip(f"Cannot load DGUV V3 graph: {e}")
        return False


async def _run_single_scenario(scenario: E2EScenario) -> JudgeVerdict:
    """Run a single scenario through the full pipeline."""
    from products.dguv_v3.chat import (
        get_or_create_session,
        coordinator_respond,
        inject_kalkulation_result,
        coordinator_summarize,
    )
    from products.dguv_v3 import DGUV_V3 as gewerk
    from engine.graph_pricing_engine import GraphPricingEngine

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
        turn_record = {
            "turn": turn_idx,
            "user": user_msg,
            "coordinator": result,
        }
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


@pytest.fixture(scope="session", autouse=True)
def load_graph():
    _ensure_graph_loaded()


PASS_THRESHOLD = 3.0


@pytest.mark.slow
@pytest.mark.parametrize(
    "scenario",
    SCENARIOS,
    ids=[s.id for s in SCENARIOS],
)
def test_e2e_scenario(scenario: E2EScenario):
    """Run a single E2E scenario and assert judge scores pass threshold."""
    verdict = asyncio.run(_run_single_scenario(scenario))

    details = []
    details.append(f"\n{'═' * 60}")
    details.append(f"  {scenario.id}: {scenario.name}")
    details.append(f"  Category: {scenario.category}")
    details.append(f"  Tricky: {scenario.tricky_aspect}")
    details.append(f"{'─' * 60}")
    for dim in JUDGE_DIMENSIONS:
        score = verdict.scores.get(dim, 0)
        reason = verdict.reasoning.get(dim, "")
        marker = "✓" if score >= 3 else "✗"
        details.append(f"  {marker} {dim:15s} {score}/5  {reason[:80]}")
    details.append(f"{'─' * 60}")
    details.append(f"  AVG: {verdict.avg_score:.1f}/5  {'PASS' if verdict.passed else 'FAIL'}")
    if verdict.error:
        details.append(f"  ERROR: {verdict.error}")
    details.append(f"{'═' * 60}")

    print("\n".join(details))

    if hasattr(verdict, "_angebote") and verdict._angebote:
        last = verdict._angebote[-1]
        print(f"  Total: {last.get('total', 0):.2f}€  Confidence: {last.get('confidence', 0)*100:.0f}%")

    assert not verdict.error, f"Judge error: {verdict.error}"
    assert verdict.avg_score >= PASS_THRESHOLD, (
        f"{scenario.id} avg score {verdict.avg_score:.1f} < {PASS_THRESHOLD}. "
        f"Scores: {verdict.scores}"
    )

    for dim, score in verdict.scores.items():
        if score <= 1:
            print(f"  ⚠ WARNING: {dim} scored {score}/5 — {verdict.reasoning.get(dim, '')}")


@pytest.mark.slow
def test_e2e_golden_reference():
    """S50 golden reference — Seniorentreff price must match pinned value."""
    from scripts.e2e_scenarios import SCENARIO_MAP
    scenario = SCENARIO_MAP["S50"]
    verdict = asyncio.run(_run_single_scenario(scenario))

    if hasattr(verdict, "_angebote") and verdict._angebote:
        last = verdict._angebote[-1]
        pruefkosten = last.get("breakdown", {}).get("pruef", 0)
        pinned = scenario.expected.get("pinned_pruefkosten", 295)
        tolerance = pinned * 0.05
        assert abs(pruefkosten - pinned) <= tolerance, (
            f"Golden reference Prüfkosten {pruefkosten:.2f}€ not within 5% of pinned {pinned}€"
        )
        print(f"  Golden reference: Prüfkosten {pruefkosten:.2f}€ ≈ {pinned}€ ✓")
