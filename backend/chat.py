"""Chat coordinator — LLM-driven conversation that triggers the ReAct agent."""

import json
import uuid
from dataclasses import dataclass, field

from llm import ClaudeLLM, HAIKU_MODEL

COORDINATOR_SYSTEM = """Du bist ein Preisberater für TÜV SÜD Elektro- und Gebäudetechnik.
Du sammelst Gebäudeinformationen vom Kunden in einem natürlichen Gespräch.

## DEIN ABLAUF
1. Begrüße den Kunden und frage nach seinem Gebäude.
2. Sammle Parameter aus dem Gespräch.
3. Sobald du MINDESTENS Gebäudetyp + BGF hast → löse Kalkulation aus.
4. Wenn die Kalkulation Rückfragen enthält, stelle sie dem Kunden.
5. Wenn der Kunde antwortet, aktualisiere die Parameter und löse eine neue Kalkulation aus.

## PARAMETER DIE DU SAMMELST
Grunddaten:
- gebaeudetyp: string (Bürogebäude | Industriegebäude | Wohngebäude | Krankenhaus | Schule | Hochhaus | Hotel | Handel | Lager | Tiefgarage | Versammlungsstätte)
- bgf_m2: number (Bruttogrundfläche in m²)
- etagen: number (Standard: 1)
- aufzuege: number (Standard: 0)
- wallboxen: number (Standard: 0)

Detailparameter (aus Rückfragen):
- anzahl_haltestellen: number (Haltestellen pro Aufzug)
- aufzugtyp: string (Personenaufzug | Lastenaufzug | Feuerwehraufzug)
- anzahl_geraete: number (ortsveränderliche elektrische Geräte)
- anzahl_stromkreise: number (Stromkreise in der Elektroanlage)
- ladetyp: string (AC | DC)
- entfernung_km: number (Entfernung zum Standort)
- anzahl_melder: number (Brandmelder)
- hat_sprachalarm: boolean (Sprachalarmanlage SAA)
- anzahl_ableitungen: number (Blitzschutz-Ableitungen)
- sprinklerflaeche_m2: number (sprinklergeschützte Fläche)
- kwp: number (PV-Leistung in kWp)
- anzahl_schaltanlagen: number (Schaltanlagen/Verteilungen)

WICHTIG: Wenn der Kunde Rückfragen beantwortet, IMMER die neuen Werte in params aufnehmen!
Gib ALLE bisher bekannten Parameter in params mit — nicht nur die neuen.

## MINIMUM für Kalkulation: gebaeudetyp + bgf_m2

## ANTWORTFORMAT
Antworte IMMER mit einem JSON-Objekt (kein Markdown, kein Text außerhalb):
{
  "message": "Deine Antwort an den Kunden (natürlich, freundlich, auf Deutsch)",
  "action": "chat" oder "calculate",
  "params": {nur bei action=calculate — alle bisher gesammelten Parameter},
  "input_summary": "nur bei action=calculate — Zusammenfassung als Eingabe für den Agenten"
}

## REGELN
- Sei freundlich aber effizient. Nicht zu viel Small Talk.
- WICHTIG: Sobald du Gebäudetyp UND BGF hast, setze action="calculate". Frage NICHT nach weiteren Details — der Agent findet Rückfragen selbst.
- Wenn der Kunde viele Infos auf einmal gibt, starte sofort die Kalkulation.
- Bei Rückfragen aus der Kalkulation: stelle maximal 3-4 Fragen auf einmal.
- Wenn der Kunde eine Empfehlung annimmt, füge den Service zur nächsten Kalkulation hinzu.
- Antworte immer auf Deutsch.
"""


@dataclass
class ChatSession:
    session_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    messages: list[dict] = field(default_factory=list)
    extracted_params: dict = field(default_factory=dict)
    last_kalkulation: dict | None = None
    turn_count: int = 0


# In-memory session store
_sessions: dict[str, ChatSession] = {}


def get_or_create_session(session_id: str | None = None) -> ChatSession:
    if session_id and session_id in _sessions:
        return _sessions[session_id]
    session = ChatSession()
    _sessions[session.session_id] = session
    return session


async def coordinator_respond(session: ChatSession, user_message: str) -> dict:
    """Call the coordinator LLM to process user message.

    Returns dict with keys: message, action, params (optional), input_summary (optional).
    """
    llm = ClaudeLLM(model=HAIKU_MODEL)

    # Add user message to history
    session.messages.append({"role": "user", "content": user_message})
    session.turn_count += 1

    # Build messages for coordinator
    messages = [
        {"role": "system", "content": COORDINATOR_SYSTEM},
        *session.messages,
    ]

    response = await llm.chat(
        messages=messages,
        max_tokens=1024,
        temperature=0.3,
    )

    # Parse JSON response
    text = response.text.strip()
    try:
        # Handle markdown code blocks
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0].strip()
        elif "```" in text:
            text = text.split("```")[1].split("```")[0].strip()
        result = json.loads(text)
    except json.JSONDecodeError:
        # Fallback: treat as plain chat
        result = {"message": text, "action": "chat"}

    # Store assistant response in history
    session.messages.append({"role": "assistant", "content": json.dumps(result, ensure_ascii=False)})

    # Update extracted params if calculation triggered
    if result.get("action") == "calculate" and result.get("params"):
        session.extracted_params.update(result["params"])
        # Ensure pipeline gets ALL known params (merge old + new)
        result["params"] = dict(session.extracted_params)
    elif result.get("params"):
        # Even on chat, store any new params for future calculations
        session.extracted_params.update(result["params"])

    return result


def inject_kalkulation_result(session: ChatSession, kalkulation: dict):
    """Feed Kalkulation result back into coordinator's conversation history."""
    session.last_kalkulation = kalkulation

    # Build a summary for the coordinator
    summary_parts = []

    positionen = kalkulation.get("positionen", [])
    if positionen:
        summary_parts.append("Positionen:")
        for p in positionen:
            summary_parts.append(f"  - {p.get('dienstleistung', '?')}: {p.get('betrag', 0):.2f}€")

    zuschlaege = kalkulation.get("zuschlaege", [])
    for z in zuschlaege:
        summary_parts.append(f"  Zuschlag: {z.get('name', '?')}: +{z.get('betrag', 0):.2f}€")

    rabatte = kalkulation.get("rabatte", [])
    for r in rabatte:
        summary_parts.append(f"  Rabatt: {r.get('name', '?')}: -{abs(r.get('betrag', 0)):.2f}€")

    gesamt = kalkulation.get("gesamtbetrag", 0)
    summary_parts.append(f"Gesamtbetrag: {gesamt:.2f}€")

    rueckfragen = kalkulation.get("rueckfragen", [])
    if rueckfragen:
        summary_parts.append("Rückfragen:")
        for q in rueckfragen:
            summary_parts.append(f"  - {q}")

    empfehlungen = kalkulation.get("empfehlungen", [])
    if empfehlungen:
        summary_parts.append("Empfehlungen:")
        for e in empfehlungen:
            summary_parts.append(f"  - {e.get('dienstleistung', '?')}: {e.get('grund', '')}")

    summary = "\n".join(summary_parts)

    session.messages.append({
        "role": "user",
        "content": (
            f"[SYSTEM: Kalkulation abgeschlossen. Ergebnis:\n{summary}\n\n"
            "Präsentiere dem Kunden das Ergebnis. "
            "Nenne den Gesamtpreis und die wichtigsten Positionen. "
            "Stelle die relevantesten Rückfragen (max 3-4). "
            "Erwähne Empfehlungen nur kurz. "
            "Antworte als JSON wie gewohnt mit action='chat'.]"
        ),
    })


async def coordinator_summarize(session: ChatSession) -> dict:
    """Have the coordinator summarize the Kalkulation result for the user."""
    llm = ClaudeLLM(model=HAIKU_MODEL)

    messages = [
        {"role": "system", "content": COORDINATOR_SYSTEM},
        *session.messages,
    ]

    response = await llm.chat(
        messages=messages,
        max_tokens=1024,
        temperature=0.3,
    )

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
