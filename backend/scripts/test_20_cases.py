"""20 multi-turn DGUV V3 test cases covering all Veit 9-Punkte requirements."""
import asyncio
import json
import httpx

API = "http://localhost:8000/api/dguv-v3"
KEY = "0a16d1b959cc4091250120505b01ed34478cc2e8d284b747727eb6ab554ec60d"
HEADERS = {"Content-Type": "application/json", "X-API-Key": KEY}

CASES = [
    # (case_id, veit_punkte, turns)
    ("C1", "P2+P7+P9", [
        "Hotel in München, 120 Zimmer, Restaurant vorhanden",
        "Reifegrad 4, letzte Prüfung 2022 für 3800 Euro",
    ]),
    ("C2", "P2b", [
        "Verwaltungsgebäude Stuttgart, 4500 m², 60% Büro, 25% Lager, 15% Serverraum",
    ]),
    ("C3", "P2+P4+P7", [
        "Grundschule Heidelberg, 25 Klassenräume, Turnhalle und Werkraum",
        "Reifegrad 2, Anlage hat Nachholbedarf",
    ]),
    ("C4", "P4", [
        "Supermarkt in Regensburg, 3000 m² Verkaufsfläche",
    ]),
    ("C5", "P2+P7", [
        "Krankenhaus Hamburg, 200 Betten",
        "Reifegrad 3, Standard",
    ]),
    ("C6", "P4+P6+P9", [
        "Industriehalle Nürnberg, 8000 m², Produktion und Schweißerei",
        "Vollerfassung gewünscht, letzte Prüfung 2023 für 6200 Euro",
    ]),
    ("C7", "P2", [
        "Tiefgarage unter Bürogebäude, 150 Stellplätze, PLZ 80331 München",
    ]),
    ("C8", "P2b+P6", [
        "Einkaufszentrum Frankfurt, 12000 m², 40% Einzelhandel, 30% Gastronomie, 20% Büro, 10% Technik",
        "Vollerfassung Messdaten gewünscht",
    ]),
    ("C9", "P4", [
        "Logistikzentrum Augsburg, 15000 m², reines Lager mit Hochregalen",
    ]),
    ("C10", "P4", [
        "Möbelhaus Ingolstadt, 6000 m² Verkaufsfläche plus 2000 m² Lager",
    ]),
    ("C11", "P2", [
        "Seniorenheim Würzburg, 80 Zimmer, mit Gemeinschaftsräumen",
    ]),
    ("C12", "P4+P7", [
        "Rechenzentrum München, 500 m², Kategorie 6 Technikräume",
        "Reifegrad 4, hochprofessionell gepflegt",
    ]),
    ("C13", "P2+P9", [
        "Hotelkette Motel One Berlin, 250 Zimmer",
        "Letzte Prüfung 2021 für 8500 Euro",
    ]),
    ("C14", "P2b", [
        "Universitätsgebäude Erlangen, 10000 m², 50% Hörsäle, 30% Labor, 20% Verwaltung",
    ]),
    ("C15", "P4+P9", [
        "Produktionshalle BMW Dingolfing, 20000 m², Kat 4",
        "Referenzpreis 2020: 15000 Euro",
    ]),
    ("C16", "P2c", [
        "Bürogebäude, 50 Meter lang, 20 Meter breit, 4 Etagen, Standort Köln",
    ]),
    ("C17", "VdS Synergie", [
        "Verwaltungsgebäude Nürnberg, 3000 m², DGUV V3 und VdS gemeinsam prüfen",
    ]),
    ("C18", "P5", [
        "Industrieanlage Mannheim, 5000 m², 25 Unterverteilungen, 3 Hauptverteilungen, NEA vorhanden",
    ]),
    ("C19", "P6", [
        "Bürogebäude Düsseldorf, 2000 m²",
        "Vollerfassung aller Messdaten gewünscht, PLZ 40213",
    ]),
    ("C20", "Multi-Anfahrt", [
        "Großes Industriegelände Leipzig, 25000 m², Kategorie 3",
    ]),
]


async def run_case(client: httpx.AsyncClient, case_id: str, punkte: str, turns: list[str]):
    session_id = None
    results = []

    for i, msg in enumerate(turns):
        body = {"message": msg}
        if session_id:
            body["session_id"] = session_id

        resp = await client.post(f"{API}/chat", headers=HEADERS, json=body, timeout=60)
        text = resp.text

        # Parse SSE
        total = None
        confidence = None
        reifegrad_step = None
        vollerfassung_step = None
        referenzpreis_step = None
        anfahrten_step = None
        action = "chat"

        for line in text.split("\n"):
            if line.startswith("data: "):
                try:
                    data = json.loads(line[6:])
                    if "session_id" in data:
                        session_id = data["session_id"]
                    if "total" in data:
                        total = data["total"]
                        confidence = data.get("confidence")
                    # Check trace steps
                    step = data.get("step", "")
                    label = data.get("label", "")
                    if step == "reifegrad":
                        reifegrad_step = label
                    if step == "vollerfassung":
                        vollerfassung_step = label
                    if step == "referenzpreis":
                        referenzpreis_step = label
                    if "Anfahrt" in label:
                        anfahrten_step = label
                except json.JSONDecodeError:
                    pass

        turn_result = {
            "turn": i + 1,
            "msg": msg[:60],
            "total": total,
            "confidence": confidence,
            "reifegrad": reifegrad_step,
            "vollerfassung": vollerfassung_step,
            "referenzpreis": referenzpreis_step,
            "anfahrten": anfahrten_step,
        }
        results.append(turn_result)

    return case_id, punkte, results


async def main():
    async with httpx.AsyncClient() as client:
        print(f"{'Case':<5} {'Veit':<16} {'Turn':<5} {'Total':>10} {'Conf':>6} {'RG':>4} {'Voll':>5} {'Ref':>4} {'Anf':>4} | Message")
        print("-" * 120)

        for case_id, punkte, turns in CASES:
            cid, p, results = await run_case(client, case_id, punkte, turns)
            for r in results:
                rg = "✓" if r["reifegrad"] else ""
                vl = "✓" if r["vollerfassung"] else ""
                rf = "✓" if r["referenzpreis"] else ""
                af = "✓" if r["anfahrten"] else ""
                total_str = f"{r['total']:.0f}€" if r['total'] else "—"
                conf_str = f"{r['confidence']*100:.0f}%" if r['confidence'] else "—"
                print(f"{cid:<5} {p:<16} T{r['turn']:<4} {total_str:>10} {conf_str:>6} {rg:>4} {vl:>5} {rf:>4} {af:>4} | {r['msg']}")
            print()


if __name__ == "__main__":
    asyncio.run(main())
