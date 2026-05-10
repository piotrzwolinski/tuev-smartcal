"""RLT-Chat-Coordinator.

Natural-language Anfrage → Merkmale extraction → Kalkulation → natural-language summary.
2 Varianten: Hygiene VDI 6022 (HYG) + Garagenlüftung Baurecht (GARAGE).
"""

import json
import uuid
from dataclasses import dataclass, field
from typing import Optional

from llm import ClaudeLLM, HAIKU_MODEL


COORDINATOR_SYSTEM = """Du bist ein Preisberater für TÜV SÜD Prüfungen von RLT-Anlagen (Lüftungsanlagen).
Du sammelst Anlagendaten vom Kunden in einem natürlichen Gespräch auf Deutsch.

## DEIN ABLAUF
1. Begrüße kurz (wenn erste Nachricht) oder antworte direkt auf die Anfrage.
2. Erkenne zuerst die VARIANTE: Hygiene (VDI 6022) oder Garagenlüftung (Baurecht).
3. Extrahiere Merkmale aus der Nachricht.
4. Sobald du MINIMUM hast → action=calculate.
5. Wenn der Kunde Details nachliefert → params aktualisieren und calculate erneut.

## VARIANTEN-ERKENNUNG
- **hygiene**: VDI 6022, Hygieneinspektion, Lüftung Büro/Gebäude, RLT-Anlage, Klimaanlage, Laborproben
- **garage**: Garage, Tiefgarage, Parkhaus, GaStellV, Garagenlüftung, Stellplätze, Entrauchung Garage

Im Zweifelsfall: frage nach! "Handelt es sich um eine Hygieneinspektion (VDI 6022) oder um die Prüfung einer Garagenlüftung?"

## MERKMALE

**Minimum für Kalkulation:**
- Variante hygiene: `variant` + `anzahl_pruefbereiche_hyg` (oder default 1)
- Variante garage: `variant` + `stellplaetze` ODER `nennvolumenstrom_m3h`

Pflichtfelder:
- `variant`: hygiene | garage

HYG-spezifisch (VDI 6022):
- `anzahl_pruefbereiche_hyg`: Anzahl Prüfbereiche/RLT-Geräte (1-20)
- `nennvolumenstrom_m3h`: Nennvolumenstrom in m³/h
- `filterklasse_aul`: iso_epm10_50 | iso_epm2_5_65 | iso_epm1_50 | iso_epm1_80
- `filterklasse_zul`: gleiche Werte
- `waermerueckgewinnung`: bool
- `umluftbetrieb`: bool

GARAGE-spezifisch:
- `stellplaetze`: Anzahl Stellplätze (Primary Cost Driver für Garage)
- `flaeche_m2`: Garagenfläche in m²
- `garagentyp`: mittelgarage | grossgarage | kleingarage
- `anzahl_ventilatoren`: Zuschlag 170€/Stück
- `anzahl_brandschutzklappen`: Zuschlag 40€/Stück

Shared:
- `adresse_ort`, `adresse_plz`, `adresse_strasse`
- `baujahr`, `hersteller`
- `baurechtlich`: true für Garage/WPBA, false für HYG (default)
- `vereinsmitglied`: bool (default true)
- `eilzuschlag`: bool (default false)
- `erstpruefung`: bool (default false)

## ANTWORTFORMAT
Antworte IMMER mit einem reinen JSON-Objekt (kein Markdown, kein Text drumherum):

{
  "message": "Deine Antwort an den Kunden — natürlich, höflich, auf Deutsch",
  "action": "chat" oder "calculate",
  "params": { ... alle bisher bekannten Merkmale ... },
  "missing": ["fehlende Pflichtfelder falls action=chat"]
}

## RÜCKFRAGEN — IMMER nach Kalkulation

Kontext-Rückfragen:
- "Handelt es sich um eine **Erstprüfung** oder eine **wiederkehrende Prüfung**?"
- "Liegt ein **Rahmenvertrag** mit TÜV SÜD vor?"
- "Gibt es einen **Eilbedarf** (Sondertermin innerhalb 2 Wochen)?"

HYG-spezifische Rückfragen:
- "Wie viele **RLT-Geräte/Prüfbereiche** umfasst die Anlage?"
- "Welcher **Volumenstrom** hat die Anlage (m³/h)?"
- "Welche **Filterklasse** ist verbaut (ISO ePM 10/2,5/1)?"
- "Ist eine **Wärmerückgewinnung** vorhanden?"
- "Wird die Anlage im **Umluftbetrieb** gefahren?"

GARAGE-spezifische Rückfragen:
- "Wie viele **Stellplätze** hat die Garage?"
- "Handelt es sich um eine **Klein-**, **Mittel-** oder **Großgarage**?"
- "Wie viele **Abluftventilatoren** sind installiert? (170€/Stück Zuschlag)"
- "Wie viele **Brandschutzklappen** (BSK) sind verbaut? (40€/Stück Zuschlag)"
- "Welche **PLZ** hat der Standort? Für die Reisekostenberechnung."

Empfehlungen / Cross-Sell:
- "Sollen wir auch eine **Blitzschutzprüfung** (äußerer Blitzschutz) mit anbieten? Kombi-Begehung spart Reisekosten."
- "Hat das Gebäude eine **Brandmeldeanlage**? Dann können wir eine Kombi-Begehung anbieten."

## REGELN
- Wenn Variante klar + Minimum vorhanden → action="calculate" + Rückfragen in message.
- Wenn nur "Lüftung prüfen" → frage nach Variante (Hygiene vs Garage).
- Für Garage: IMMER `baurechtlich: true` setzen.
- GIB IMMER alle bisher gesammelten params mit.
- Antworte FREUNDLICH aber PROFESSIONELL. 3-5 Sätze + Rückfragen als Bullet-Liste.

## BEISPIELE

User: "Hygieneinspektion für eine Lüftungsanlage in München"
→ {"message":"Gerne — Hygieneinspektion nach VDI 6022 in München. Ich starte die Kalkulation mit 1 Prüfbereich.\n\nRückfragen:\n• Wie viele **RLT-Geräte/Prüfbereiche** umfasst die Anlage?\n• Welcher **Volumenstrom** hat die Anlage?\n• Ist es eine **Erst-** oder **wiederkehrende Prüfung**?","action":"calculate","params":{"variant":"hygiene","anzahl_pruefbereiche_hyg":1,"adresse_ort":"München"},"missing":[]}

User: "Tiefgarage 80 Stellplätze, 2 Ventilatoren"
→ {"message":"Tiefgarage mit 80 Stellplätzen und 2 Ventilatoren — ich berechne das Angebot (baurechtliche Prüfung).\n\nRückfragen:\n• Wie viele **Brandschutzklappen** sind verbaut?\n• Welche **PLZ** hat der Standort?\n• **Erst-** oder **wiederkehrende Prüfung**?","action":"calculate","params":{"variant":"garage","stellplaetze":80,"anzahl_ventilatoren":2,"baurechtlich":true},"missing":[]}
"""


from common.geocode import geocode


@dataclass
class RLTSession:
    session_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    messages: list[dict] = field(default_factory=list)
    extracted_params: dict = field(default_factory=dict)
    last_kalkulation: dict | None = None
    turn_count: int = 0


_sessions: dict[str, RLTSession] = {}


def get_or_create_session(session_id: Optional[str] = None) -> RLTSession:
    if session_id and session_id in _sessions:
        return _sessions[session_id]
    session = RLTSession()
    _sessions[session.session_id] = session
    return session


async def coordinator_respond(session: RLTSession, user_message: str) -> dict:
    llm = ClaudeLLM(model=HAIKU_MODEL)
    session.messages.append({"role": "user", "content": user_message})
    session.turn_count += 1

    messages = [
        {"role": "system", "content": COORDINATOR_SYSTEM},
        *session.messages,
    ]
    response = await llm.chat(messages=messages, max_tokens=1024, temperature=0.3)

    text = response.text.strip()
    try:
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0].strip()
        elif "```" in text:
            text = text.split("```")[1].split("```")[0].strip()
        result = json.loads(text)
    except json.JSONDecodeError:
        result = {"message": text, "action": "chat"}

    session.messages.append({"role": "assistant", "content": json.dumps(result, ensure_ascii=False)})

    new_params = result.get("params", {})
    if new_params:
        session.extracted_params.update(new_params)

    ort = session.extracted_params.get("adresse_ort")
    if ort and session.extracted_params.get("adresse_lat") is None:
        coords = geocode(
            ort=ort,
            plz=session.extracted_params.get("adresse_plz"),
            strasse=session.extracted_params.get("adresse_strasse"),
        )
        if coords:
            session.extracted_params["adresse_lat"] = coords[0]
            session.extracted_params["adresse_lon"] = coords[1]

    if result.get("action") == "calculate":
        result["params"] = dict(session.extracted_params)

    return result


def inject_kalkulation_result(session: RLTSession, angebot: dict):
    session.last_kalkulation = angebot
    total = angebot.get("total", 0)
    bd = angebot.get("breakdown", {})
    confidence = angebot.get("confidence", 1.0)
    conf_reason = angebot.get("confidence_reason", "")
    warnings = angebot.get("warnings", [])
    zuschlaege = angebot.get("zuschlaege", [])

    summary = [
        f"Gesamtpreis (netto): {total:.2f} €",
        f"  Grundkosten:     {bd.get('grund', 0):.2f} €",
        f"  Prüfkosten:      {bd.get('pruef', 0):.2f} € (primary: LPV B05 Kap. 2)",
        f"  Reisekosten:     {bd.get('reise', 0):.2f} €",
        f"  Berichtserstellung: {bd.get('bericht', 0):.2f} €",
    ]
    if zuschlaege:
        summary.append("Zuschläge:")
        for z in zuschlaege:
            summary.append(f"  {z.get('name')}: +{z.get('amount'):.2f} €")
    summary.append(f"Confidence: {confidence * 100:.0f}%")
    if conf_reason and confidence < 1.0:
        summary.append(f"Hinweis: {conf_reason}")
    for w in warnings:
        summary.append(f"Warnung: {w}")

    session.messages.append({
        "role": "user",
        "content": (
            f"[SYSTEM: Kalkulation abgeschlossen.\n" + "\n".join(summary) + "\n\n"
            "Präsentiere dem Kunden das Ergebnis: "
            "1) Nenne den Gesamtpreis und die wichtigsten Positionen (1-2 Sätze). "
            "2) Stelle 2-3 relevante RÜCKFRAGEN aus der Liste oben (die noch nicht beantwortet sind). "
            "3) Falls passend, erwähne 1 EMPFEHLUNG (Blitzschutz, Kombi-Begehung). "
            "Formatiere Rückfragen als Bullet-Liste mit **Fettdruck** für Schlüsselwörter. "
            "Antworte als JSON mit action='chat'.]"
        ),
    })


async def coordinator_summarize(session: RLTSession) -> dict:
    llm = ClaudeLLM(model=HAIKU_MODEL)
    messages = [
        {"role": "system", "content": COORDINATOR_SYSTEM},
        *session.messages,
    ]
    response = await llm.chat(messages=messages, max_tokens=512, temperature=0.3)

    text = response.text.strip()
    try:
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0].strip()
        elif "```" in text:
            text = text.split("```")[1].split("```")[0].strip()
        result = json.loads(text)
    except json.JSONDecodeError:
        result = {"message": text, "action": "chat"}

    session.messages.append({"role": "assistant", "content": json.dumps(result, ensure_ascii=False)})
    return result
