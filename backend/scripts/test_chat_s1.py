"""Test chat coordinator against S1 complaints from Testrunde 08.06.

Sends real user messages through the LIVE API endpoint and checks:
1. Does bot ask about m² when it shouldn't?
2. Does bot calculate immediately when sufficient data provided?
3. Do proxy questions (Zimmer, Betten) still work?

Requires: backend running on localhost:8000 with SMARTCAL_API_KEY.
"""

import os
import json
import httpx
import asyncio

API_BASE = "http://localhost:8000"
API_KEY = os.getenv("SMARTCAL_API_KEY", "0a16d1b959cc4091250120505b01ed34478cc2e8d284b747727eb6ab554ec60d")

M2_QUESTION_PATTERNS = [
    "wie groß ist",
    "gesamtfläche nennen",
    "fläche in m²",
    "fläche nennen",
    "quadratmeter nennen",
    "fläche angeben",
    "wie viele m²",
    "können sie die fläche",
    "benötige.*fläche",
    "benötige.*m²",
]


def has_m2_question(msg: str) -> bool:
    """Check if message ASKS about m² — mentions of m² in results/explanations don't count."""
    import re
    lower = msg.lower()
    return any(re.search(p, lower) for p in M2_QUESTION_PATTERNS)


async def chat(client: httpx.AsyncClient, message: str, session_id: str = None) -> dict:
    """Send a chat message and collect SSE responses."""
    payload = {"message": message, "gewerk": "dguv_v3"}
    if session_id:
        payload["session_id"] = session_id

    messages = []
    traces = []
    result_data = None
    calculated = False

    async with client.stream(
        "POST", f"{API_BASE}/api/dguv-v3/chat",
        json=payload,
        headers={"X-API-Key": API_KEY},
        timeout=30.0,
    ) as response:
        current_event = None
        async for line in response.aiter_lines():
            line = line.strip()
            if not line:
                current_event = None
                continue
            if line.startswith("event: "):
                current_event = line[7:]
            elif line.startswith("data: "):
                raw = line[6:]
                try:
                    data = json.loads(raw)
                except json.JSONDecodeError:
                    continue
                if current_event == "session" and isinstance(data, dict):
                    session_id = data.get("session_id", session_id)
                elif current_event == "message" and isinstance(data, dict):
                    content = data.get("content", "")
                    if content:
                        messages.append(content)
                elif current_event == "trace":
                    calculated = True
                    if isinstance(data, dict):
                        traces.append(data)
                elif current_event == "result" and isinstance(data, dict):
                    result_data = data
                    calculated = True

    full_message = "\n".join(messages)
    return {
        "session_id": session_id,
        "message": full_message,
        "calculated": calculated,
        "total": result_data.get("total") if result_data else None,
        "traces": traces,
        "has_m2_question": has_m2_question(full_message),
    }


async def run_tests():
    async with httpx.AsyncClient() as client:
        results = []

        # ═══ S1 SCENARIOS — bot should NOT ask about m² ═══

        print("=" * 100)
        print("S1 COMPLAINT SCENARIOS — bot should NOT ask about m²")
        print("=" * 100)

        s1_cases = [
            {
                "id": "S1-1",
                "tester": "Pausch",
                "complaint": '"48 UV auf 4 Gebäude — hat ständig auf m² herumgeritten"',
                "message": "Ich möchte eine DGUV V3 Prüfung für ein Verwaltungsgebäude mit 48 Unterverteilungen auf 4 Gebäude verteilt.",
                "expect_calc": True,
                "expect_no_m2": True,
            },
            {
                "id": "S1-2",
                "tester": "Steinwidder",
                "complaint": '"545 ortsveränderliche Geräte RZ — Quadratmeter haben wir nicht"',
                "message": "Rechenzentrum, 545 ortsveränderliche Geräte prüfen",
                "expect_calc": True,
                "expect_no_m2": True,
            },
            {
                "id": "S1-3",
                "tester": "Pausch",
                "complaint": '"Schaltschrank prüfen — wollte unbedingt Mitarbeiter haben"',
                "message": "Ich möchte einen Schaltschrank prüfen lassen",
                "expect_calc": True,
                "expect_no_m2": True,
            },
            {
                "id": "S1-4",
                "tester": "Weiß",
                "complaint": '"UV und Maschinen — wollte immer zu m² zurück"',
                "message": "Industriegebäude, 12 Unterverteilungen und diverse Produktionsmaschinen",
                "expect_calc": True,
                "expect_no_m2": True,
            },
            {
                "id": "S1-5",
                "tester": "Weiß",
                "complaint": '"20 ortsveränderliche Geräte Kindergarten — System hat abgelehnt"',
                "message": "20 ortsveränderliche Geräte in einem Kindergarten in Waiblingen prüfen",
                "expect_calc": True,
                "expect_no_m2": True,
            },
        ]

        for case in s1_cases:
            print(f"\n{'─'*80}")
            print(f"  {case['id']} — {case['tester']}")
            print(f"  Complaint: {case['complaint']}")
            print(f"  Input: \"{case['message']}\"")

            r = await chat(client, case["message"])

            calc_ok = r["calculated"] == case["expect_calc"]
            m2_ok = (not r["has_m2_question"]) == case["expect_no_m2"]
            passed = calc_ok and m2_ok

            status = "✅ PASS" if passed else "❌ FAIL"
            print(f"  {status}")
            print(f"    Calculated: {r['calculated']} (expected {case['expect_calc']})")
            print(f"    m² question: {r['has_m2_question']} (expected {not case['expect_no_m2']})")
            if r["total"]:
                print(f"    Total: {r['total']:,.0f} €")
            print(f"    Bot says: \"{r['message'][:120]}{'...' if len(r['message'])>120 else ''}\"")

            results.append({"case": case["id"], "passed": passed, "type": "S1"})

        # ═══ PROXY SCENARIOS — bot SHOULD ask proxy questions ═══

        print(f"\n{'=' * 100}")
        print("PROXY SCENARIOS — bot SHOULD ask proxy questions (Zimmer, Betten, etc.)")
        print("=" * 100)

        proxy_cases = [
            {
                "id": "P1",
                "desc": "Hotel ohne Größe → soll nach Zimmern fragen",
                "message": "Hotel in München, DGUV V3 Prüfung",
                "expect_calc": False,
                "expect_proxy": "zimmer",
            },
            {
                "id": "P2",
                "desc": "Krankenhaus ohne Größe → soll nach Betten fragen",
                "message": "Krankenhaus prüfen, DGUV V3",
                "expect_calc": False,
                "expect_proxy": "bett",
            },
            {
                "id": "P3",
                "desc": "Büro ohne alles → darf nach m² fragen (legitimate!)",
                "message": "Bürogebäude, DGUV V3 Prüfung",
                "expect_calc": False,
                "expect_proxy": None,
            },
            {
                "id": "P4",
                "desc": "Hotel + 120 Zimmer → soll sofort kalkulieren",
                "message": "Hotel in München, 120 Zimmer, DGUV V3 Prüfung",
                "expect_calc": True,
                "expect_proxy": None,
            },
        ]

        for case in proxy_cases:
            print(f"\n{'─'*80}")
            print(f"  {case['id']} — {case['desc']}")
            print(f"  Input: \"{case['message']}\"")

            r = await chat(client, case["message"])

            calc_ok = r["calculated"] == case["expect_calc"]
            if case["expect_proxy"]:
                proxy_ok = case["expect_proxy"].lower() in r["message"].lower()
            else:
                proxy_ok = True

            passed = calc_ok and proxy_ok
            status = "✅ PASS" if passed else "❌ FAIL"
            print(f"  {status}")
            print(f"    Calculated: {r['calculated']} (expected {case['expect_calc']})")
            if case["expect_proxy"]:
                print(f"    Proxy '{case['expect_proxy']}' in message: {proxy_ok}")
            if r["total"]:
                print(f"    Total: {r['total']:,.0f} €")
            print(f"    Bot says: \"{r['message'][:150]}{'...' if len(r['message'])>150 else ''}\"")

            results.append({"case": case["id"], "passed": passed, "type": "PROXY"})

        # ═══ SUMMARY ═══

        print(f"\n{'=' * 100}")
        s1_pass = sum(1 for r in results if r["type"] == "S1" and r["passed"])
        s1_total = sum(1 for r in results if r["type"] == "S1")
        proxy_pass = sum(1 for r in results if r["type"] == "PROXY" and r["passed"])
        proxy_total = sum(1 for r in results if r["type"] == "PROXY")
        print(f"S1 complaints fixed: {s1_pass}/{s1_total}")
        print(f"Proxy flows preserved: {proxy_pass}/{proxy_total}")
        print(f"Total: {s1_pass + proxy_pass}/{s1_total + proxy_total}")
        print("=" * 100)


if __name__ == "__main__":
    asyncio.run(run_tests())
