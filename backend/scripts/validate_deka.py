"""Validate SmartCal DGUV engine vs DEKA Großkunden actual prices.

3 Bürogebäude in München with known equipment-level pricing from DEKA.
Runs multiturn chat conversations and compares output with actuals.
"""

import asyncio
import json
import httpx

API = "http://localhost:8000"
KEY = "0a16d1b959cc4091250120505b01ed34478cc2e8d284b747727eb6ab554ec60d"
HEADERS = {"x-api-key": KEY, "content-type": "application/json"}

# DEKA actual prices (from Preismatrix xlsx, "Allgemeine Elektroanlagen" section only)
DEKA_CASES = [
    {
        "name": "Barthstr 12-22 (KONDO)",
        "eq": "3268262",
        "pruefgrundlage": "VdS",
        "elektro_summe": 9733.0,
        "blitzschutz": 3316.0,
        "bma": 1393.0,
        "sibe": 5254.0,
        "total_all": 9733 + 5254 + 1283 + 2570 + 3316 + 1393 + 843 + 1514 + 2242 + 300 + 1596 + 4598,
        # Estimated m² from UV counts: 10+2 NSHV + 15+33+1+2 UV, 75 Trennstellen, 400SP garage
        "estimated_m2": [6000, 8000, 10000],
        "turns": [
            "Bürogebäude in München, Barthstraße 12-22, ca. 8000 m²",
            "VdS-Prüfung bitte mit anbieten",
            "PLZ 80339, Reifegrad 3, keine Vollerfassung",
        ],
    },
    {
        "name": "Landsberger Str 84-90 (MK2)",
        "eq": "3256171",
        "pruefgrundlage": "kombiniert (DGUV+VdS)",
        "elektro_summe": 15078.0,
        "blitzschutz": 3213.0,
        "bma": 1512.0,
        "sibe": 3577.0,
        "total_all": 15078 + 3577 + 3213 + 1512 + 2241 + 1182 + 1685 + 5018 + 2531,
        # 4+5 NSHV + 13+36+5+7 UV, 231 Einzelbatterieleuchten, 72 Ableiter, 200SP, 3 RLT
        "estimated_m2": [8000, 12000, 15000],
        "turns": [
            "Bürogebäude in München, Landsberger Straße 84-90, ungefähr 12000 Quadratmeter",
            "Ja, VdS-Prüfung zusammen mit DGUV bitte. Kombinierte Prüfung.",
            "PLZ 80339",
        ],
    },
    {
        "name": "Landsberger Str 94-98 (MK1)",
        "eq": "3256175",
        "pruefgrundlage": "DGUV A3",
        "elektro_summe": 5255.0,
        "blitzschutz": 1704.0,
        "bma": 1008.0,
        "sibe": 1150.0,
        "total_all": 5255 + 1150 + 1704 + 1008 + 637 + 926 + 937,
        # 1 NSHV + 6+16+3 UV, 63 Einzelbatterieleuchten, 14 Trennstellen, 50SP
        "estimated_m2": [3000, 4000, 5000],
        "turns": [
            "Bürogebäude München, Landsberger Straße 94-98, rund 4000 m²",
            "Nur DGUV V3, keine VdS",
            "80339 München, Zustand ist ordentlich",
        ],
    },
]


async def parse_sse(response_text: str) -> dict:
    """Parse SSE stream into events."""
    events = []
    current_event = None
    current_data = []

    for line in response_text.split("\n"):
        line = line.strip()
        if line.startswith("event:"):
            current_event = line[6:].strip()
        elif line.startswith("data:"):
            data_str = line[5:].strip()
            try:
                data = json.loads(data_str)
            except json.JSONDecodeError:
                data = data_str
            events.append({"event": current_event, "data": data})
        elif line == "":
            current_event = None

    return events


async def run_conversation(client: httpx.AsyncClient, case: dict) -> dict:
    """Run a multiturn chat conversation for a DEKA case."""
    session_id = None
    results = {"name": case["name"], "turns": [], "angebot": None}

    for i, msg in enumerate(case["turns"]):
        payload = {"message": msg, "mode": "graph"}
        if session_id:
            payload["session_id"] = session_id

        resp = await client.post(
            f"{API}/api/dguv-v3/chat",
            headers=HEADERS,
            json=payload,
            timeout=60.0,
        )

        raw = resp.text
        events = await parse_sse(raw)

        # Extract session_id from first response
        for ev in events:
            if ev["event"] == "session" and isinstance(ev["data"], dict):
                session_id = ev["data"].get("session_id", session_id)

        # Extract angebot
        for ev in events:
            if ev["event"] == "angebot" and isinstance(ev["data"], dict):
                results["angebot"] = ev["data"]

        # Extract assistant message
        for ev in events:
            if ev["event"] == "message" and isinstance(ev["data"], dict):
                content = ev["data"].get("content", "")
                results["turns"].append({
                    "turn": i + 1,
                    "user": msg,
                    "assistant": content[:200] + "..." if len(content) > 200 else content,
                })

        await asyncio.sleep(0.5)

    return results


async def run_direct_calculate(client: httpx.AsyncClient, m2: float, vds: bool = False) -> dict:
    """Direct /calculate call for quick sweep."""
    payload = {
        "nutzung": "buerogebaeude",
        "gesamtflaeche_m2": m2,
        "primary_installationskategorie": 2,
        "adresse_ort": "München",
        "adresse_plz": "80339",
        "vds_pruefung": vds,
    }
    resp = await client.post(
        f"{API}/api/dguv-v3/calculate",
        headers=HEADERS,
        json=payload,
        timeout=30.0,
    )
    return resp.json()


async def main():
    async with httpx.AsyncClient() as client:
        # ─── Part 1: Direct calculate sweep to find matching m² ───
        print("=" * 80)
        print("PART 1: m² SWEEP — What m² produces DEKA-matching prices?")
        print("=" * 80)

        for case in DEKA_CASES:
            print(f"\n{'─' * 60}")
            print(f"  {case['name']}")
            print(f"  DEKA actual (Allg. Elektro): {case['elektro_summe']:,.0f} €")
            print(f"  Prüfgrundlage: {case['pruefgrundlage']}")
            print(f"{'─' * 60}")

            vds = "VdS" in case["pruefgrundlage"]

            for m2 in case["estimated_m2"]:
                result = await run_direct_calculate(client, m2, vds=vds)
                total = result.get("total", 0)
                delta = ((total - case["elektro_summe"]) / case["elektro_summe"]) * 100
                marker = " ◄ CLOSEST" if abs(delta) < 30 else ""
                print(f"    {m2:>6,} m²  →  {total:>10,.2f} €  (Δ {delta:+6.1f}%){marker}")

        # ─── Part 2: Multiturn chat conversations ───
        print("\n" + "=" * 80)
        print("PART 2: MULTITURN CHAT CONVERSATIONS")
        print("=" * 80)

        for case in DEKA_CASES:
            print(f"\n{'━' * 70}")
            print(f"  CASE: {case['name']}")
            print(f"  DEKA actual: {case['elektro_summe']:,.0f} € ({case['pruefgrundlage']})")
            print(f"{'━' * 70}")

            result = await run_conversation(client, case)

            for turn in result["turns"]:
                print(f"\n  Turn {turn['turn']}:")
                print(f"    User: {turn['user']}")
                print(f"    Bot:  {turn['assistant']}")

            if result["angebot"]:
                a = result["angebot"]
                total = a.get("total", 0)
                bd = a.get("breakdown", {})
                delta = ((total - case["elektro_summe"]) / case["elektro_summe"]) * 100
                zusatz = a.get("zusatzleistungen", [])
                zusatz_total = sum(z.get("preis", 0) for z in zusatz)

                print(f"\n  ┌─ ANGEBOT ─────────────────────────────────────")
                print(f"  │ Grundkosten:    {bd.get('grund', 0):>10,.2f} €")
                print(f"  │ Prüfkosten:     {bd.get('pruef', 0):>10,.2f} €")
                print(f"  │ Reisekosten:    {bd.get('reise', 0):>10,.2f} €")
                print(f"  │ Bericht:        {bd.get('bericht', 0):>10,.2f} €")
                for z in a.get("zuschlaege", []):
                    print(f"  │ {z.get('name', '?'):16s}{z.get('amount', 0):>10,.2f} €")
                print(f"  │ ──────────────────────────────────")
                print(f"  │ TOTAL:          {total:>10,.2f} €")
                if zusatz:
                    print(f"  │")
                    for z in zusatz:
                        print(f"  │ + {z.get('name', '?'):14s}{z.get('preis', 0):>10,.2f} €")
                    print(f"  │ TOTAL+Zusatz:   {total + zusatz_total:>10,.2f} €")
                print(f"  │")
                print(f"  │ DEKA actual:    {case['elektro_summe']:>10,.0f} €")
                print(f"  │ Delta:          {delta:>+9.1f}%")
                accuracy = 100 - abs(delta)
                status = "✓ PASS" if abs(delta) <= 20 else "✗ FAIL"
                print(f"  │ Accuracy:       {accuracy:>9.1f}%  {status}")
                print(f"  │ Confidence:     {a.get('confidence', 0)*100:>9.0f}%")
                print(f"  └─────────────────────────────────────────────")
            else:
                print("\n  ⚠ NO ANGEBOT RECEIVED")

        print("\n" + "=" * 80)
        print("VALIDATION COMPLETE")
        print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
