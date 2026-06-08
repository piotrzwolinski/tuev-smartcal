"""Blitzschutz-Chat-Coordinator.

Natural-language Anfrage → Merkmale extraction → Kalkulation → natural-language summary.

Analog to root chat.py (smartcal), but specialized for Blitzschutz:
- LPV-based pricing (not graph-ReAct)
- Deterministic calculation via PricingEngine + BLITZSCHUTZ
- Coordinator prompts in German for TÜV users
"""

import json
import re
import uuid
from dataclasses import dataclass, field
from typing import Optional

from llm import ClaudeLLM, HAIKU_MODEL


COORDINATOR_SYSTEM = """Du bist ein Preisberater für TÜV SÜD Blitzschutz-Prüfungen.
Du sammelst Anlagendaten vom Kunden in einem natürlichen Gespräch auf Deutsch.

## DEIN ABLAUF
1. Begrüße kurz (wenn erste Nachricht) oder antworte direkt auf die Anfrage.
2. Extrahiere Merkmale aus der Nachricht (auch aus beiläufig erwähnten Details).
3. Sobald du MINIMUM hast → action=calculate.
4. Wenn der Kunde Details nachliefert → aktualisiere params und calculate erneut.

## MERKMALE DIE DU EXTRAHIERST

**Minimum für Kalkulation:** nutzung + (anzahl_ableitungen ODER gesamtflaeche_m2)
Wenn der Kunde m² angibt aber keine Ableitungen kennt → action=calculate SOFORT. Das System schätzt die Ableitungen aus der Gebäudefläche.
Wenn der Kunde NUR den Gebäudetyp nennt (ohne m² UND ohne Ableitungen) → frage nach m² ODER Ableitungen.

Pflichtfelder:
- `nutzung`: schule | buero | industrie | wohnung | hotel | museum | krankenhaus | lager | garage | sonstige
- `gesamtflaeche_m2`: Gebäudefläche in m² (alternativ zu anzahl_ableitungen)
  Hinweise: "Kita"/"Kindergarten"/"Gymnasium"/"Turnhalle" → schule ; "Kirche"/"Burg"/"Schloss" → museum ; "Altenheim"/"Pflegeheim" → krankenhaus
- `anzahl_ableitungen`: Anzahl Trennstellen / Messstellen (1-500, Primary Cost-Driver)

Optional (verwende wenn erwähnt):
- `schutzklasse`: I | II | III | IV (DIN EN 62305)
- `adresse_ort`: Stadt/Ort (z.B. "Reichenberg", "Würzburg", "Schweinfurt")
- `adresse_plz`: 5-stellige deutsche Postleitzahl (z.B. "97234"). Extrahiere IMMER wenn vorhanden — wichtig zur Disambiguierung bei kleinen Orten (z.B. Reichenberg existiert mehrfach in DE).
- `adresse_strasse`: Straße + Hausnummer wenn vorhanden
- `vereinsmitglied`: bool (TÜV SÜD Verein, default true)
- `eilzuschlag`: bool (+25% Sondertermin, default false)
- `erstpruefung`: bool (+100% Erstprüfung, default false)
- `baurechtlich`: bool (§2 SPrüfV Sonderbau, default false)
- `laenge_m`, `breite_m`, `hoehe_m`: Gebäudedimensionen
- `bauart`: ziegel | stahlbeton | holz | stahl | gemischt | naturstein
- `dacheindeckung`: blech | kies | folie | ziegel | dachpappe | gruendach
- `material_ableitung`: kupfer | alulegierung | stahl_verzinkt | edelstahl | metallene_fassade

## ANTWORTFORMAT
Antworte IMMER mit einem reinen JSON-Objekt (kein Markdown, kein Text drumherum):

{
  "message": "Deine Antwort an den Kunden — natürlich, höflich, auf Deutsch",
  "action": "chat" oder "calculate",
  "params": { ... alle bisher bekannten Merkmale ... },
  "missing": ["fehlende Pflichtfelder falls action=chat"]
}

## RÜCKFRAGEN — IMMER nach Kalkulation

Auch wenn du genug für eine Kalkulation hast, stelle IMMER 2-4 Rückfragen aus dieser Liste
(wähle die relevantesten basierend auf dem was der Kunde NOCH NICHT gesagt hat):

Kontext-Rückfragen:
- "Handelt es sich um eine **Erstprüfung** (vor Inbetriebnahme) oder eine **wiederkehrende Prüfung**?" (falls nicht klar)
- "Ist das Gebäude ein **Sonderbau** (Krankenhaus, Versammlungsstätte, Hochhaus >22m)? Dann gilt §2 SPrüfV mit gesonderter Preislogik."
- "Liegt ein **Rahmenvertrag** mit TÜV SÜD vor, oder handelt es sich um einen Einzelauftrag?" (Vereinsmitglied-Status)
- "Gibt es einen **Eilbedarf** (Sondertermin innerhalb 2 Wochen)?"
- "Welche **Schutzklasse** hat die Anlage? (I = Ex/Munition, II = Krankenhaus/Museum, III = Standard, IV = einfaches Lager)" (falls nicht angegeben)

Technische Rückfragen (für präzisere Kalkulation):
- "Wie viele **Teilgebäude** umfasst die Anlage? Bei Komplexen (z.B. Schule + Turnhalle) rechnen wir pro Gebäude."
- "Welches **Material** haben die Ableitungen? (Kupfer / Aluminium / verzinkter Stahl / metallene Fassade)"
- "Welcher **Typ Erdungsanlage** liegt vor? (Fundamenterder / Tiefenerder)"
- "Welche **PLZ** hat der Standort? Für die exakte Reisekostenberechnung zum nächsten TÜV-Standort."

Empfehlungen / Cross-Sell:
- "Sollen wir auch den **inneren Blitzschutz** (Überspannungsschutz, LPV B04 §8.2) mit anbieten? Das wird häufig zusammen beauftragt."
- "Bei Schulen/öffentlichen Gebäuden ist oft auch eine **RLT-Hygieneinspektion** (VDI 6022) fällig — soll ich das mit kalkulieren?"
- "Hat das Gebäude eine **Brandmeldeanlage**? Dann können wir eine Kombi-Begehung anbieten (Reisekostenvorteil)."

## REGELN
- Wenn nutzung + (anzahl_ableitungen ODER gesamtflaeche_m2) vorhanden → SOFORT action="calculate". IMMER kalkulieren, auch grob!
- Wenn nur "Gebäude mit Blitzschutz" ohne m² UND ohne Ableitungen → action="chat", frage nach m² ODER Ableitungen.
- Wenn Schutzklasse fehlt → calculate mit Fallback, aber FRAGE danach in der message.
- Wenn Kunde auf Rückfragen antwortet → params aktualisieren + NEU berechnen.
- GIB IMMER alle bisher gesammelten params mit — nicht nur neue!
- Antworte FREUNDLICH aber PROFESSIONELL. 3-5 Sätze + Rückfragen als Bullet-Liste.

## BEISPIELE

User: "ich brauch ein Angebot für ne Schule, 35 Messstellen, Würzburg, Klasse III"
→ {"message":"Sehr gerne — Schule in Würzburg, 35 Messstellen, Schutzklasse III. Ich starte die Kalkulation.\n\nEin paar Rückfragen für die Präzisierung:\n• Handelt es sich um eine **Erstprüfung** oder eine **wiederkehrende Prüfung**?\n• Umfasst die Schule **mehrere Gebäude** (z.B. Hauptgebäude + Turnhalle)?\n• Sollen wir den **inneren Blitzschutz** (Überspannungsschutz) mit anbieten?","action":"calculate","params":{"nutzung":"schule","anzahl_ableitungen":35,"schutzklasse":"III","adresse_ort":"Würzburg"},"missing":[]}

User: "Lagerhalle in Nürnberg, 2.500 m², Blitzschutzklasse 3"
→ {"message":"Lagerhalle in Nürnberg, 2.500 m², Schutzklasse III. Ich schätze die Ableitungen aus der Gebäudefläche und starte eine Grobkalkulation.\n\nFür eine präzisere Kalkulation:\n• **Wie viele Ableitungen/Messstellen** hat die Anlage?\n• Handelt es sich um eine **Erstprüfung** oder **wiederkehrende Prüfung**?\n• Welches **Material** haben die Ableitungen?","action":"calculate","params":{"nutzung":"lager","gesamtflaeche_m2":2500,"schutzklasse":"III","adresse_ort":"Nürnberg"},"missing":[]}

User: "ich hab ne Halle"
→ {"message":"Eine Halle — gerne! Damit ich Ihnen ein Angebot erstellen kann:\n\n• **Wie groß ist die Halle** (m² oder Länge × Breite)?\n• Alternativ: **Wie viele Messstellen/Ableitungen** hat die Blitzschutzanlage?\n• In **welcher Stadt** befindet sich das Gebäude?","action":"chat","params":{"nutzung":"lager"},"missing":["gesamtflaeche_m2 oder anzahl_ableitungen"]}

User: "Kindergarten in München, 8 Ableitungen"
→ {"message":"Kindergarten in München, 8 Ableitungen — ich berechne das Angebot. Die Schutzklasse nehme ich mit **III** (Standard für Schulen/Kindergärten) an.\n\nRückfragen:\n• Stimmt die Schutzklasse III, oder liegt eine andere Einstufung vor?\n• Ist es eine **Erst-** oder **Wiederholungsprüfung**?\n• Besteht ein **Rahmenvertrag** mit TÜV SÜD?","action":"calculate","params":{"nutzung":"schule","anzahl_ableitungen":8,"adresse_ort":"München"},"missing":[]}

User: "ja, Erstprüfung, kein Rahmenvertrag"
→ {"message":"Danke — ich aktualisiere: **Erstprüfung** (+100% Zuschlag) und **kein Vereinsmitglied** (+20%). Neue Kalkulation wird erstellt.","action":"calculate","params":{"nutzung":"schule","anzahl_ableitungen":8,"adresse_ort":"München","erstpruefung":true,"vereinsmitglied":false},"missing":[]}
"""


from common.geocode import geocode



def _parse_llm_json(text: str) -> dict:
    """Parse LLM response that should be JSON but may have extra text."""
    text = text.strip()
    # Try direct parse
    try:
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0].strip()
        elif "```" in text:
            text = text.split("```")[1].split("```")[0].strip()
        return json.loads(text)
    except (json.JSONDecodeError, IndexError):
        pass
    # Try extracting JSON object from text
    match = re.search(r'\{[\s\S]*\}', text)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass
    return {"message": text, "action": "chat"}

@dataclass
class BlitzschutzSession:
    session_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    messages: list[dict] = field(default_factory=list)
    extracted_params: dict = field(default_factory=dict)
    last_kalkulation: dict | None = None
    last_calc_params: dict = field(default_factory=dict)
    turn_count: int = 0


_sessions: dict[str, BlitzschutzSession] = {}


def get_or_create_session(session_id: Optional[str] = None) -> BlitzschutzSession:
    if session_id and session_id in _sessions:
        return _sessions[session_id]
    session = BlitzschutzSession()
    _sessions[session.session_id] = session
    return session


async def coordinator_respond(session: BlitzschutzSession, user_message: str) -> dict:
    llm = ClaudeLLM(model=HAIKU_MODEL)
    session.messages.append({"role": "user", "content": user_message})
    session.turn_count += 1

    messages = [
        {"role": "system", "content": COORDINATOR_SYSTEM},
        *session.messages,
    ]
    response = await llm.chat(messages=messages, max_tokens=1024, temperature=0.3)

    text = response.text.strip()
    result = _parse_llm_json(text)

    session.messages.append({"role": "assistant", "content": json.dumps(result, ensure_ascii=False)})

    # Aktualizuj session z nowymi params
    new_params = result.get("params", {})
    if new_params:
        session.extracted_params.update(new_params)

    # Auto-geokoduj adresse_ort/plz/strasse → adresse_lat/lon
    ort = session.extracted_params.get("adresse_ort")
    plz = session.extracted_params.get("adresse_plz")
    if (ort or plz) and session.extracted_params.get("adresse_lat") is None:
        coords = geocode(
            ort=ort,
            plz=plz,
            strasse=session.extracted_params.get("adresse_strasse"),
        )
        if coords:
            session.extracted_params["adresse_lat"] = coords[0]
            session.extracted_params["adresse_lon"] = coords[1]

    # If calculate, pass all accumulated params
    has_minimum = session.extracted_params.get("nutzung") and (session.extracted_params.get("anzahl_ableitungen") or session.extracted_params.get("gesamtflaeche_m2"))
    if result.get("action") == "calculate":
        result["params"] = dict(session.extracted_params)
    elif session.last_kalkulation and has_minimum:
        result["action"] = "calculate"
        result["params"] = dict(session.extracted_params)

    return result


def inject_kalkulation_result(session: BlitzschutzSession, angebot: dict):
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
        f"  Prüfkosten:      {bd.get('pruef', 0):.2f} € (primary: LPV B04 §8.1)",
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
            "3) Falls passend, erwähne 1 EMPFEHLUNG (innerer Blitzschutz, RLT, Kombi-Begehung). "
            "Formatiere Rückfragen als Bullet-Liste mit **Fettdruck** für Schlüsselwörter. "
            "Antworte als JSON. Wenn der Kunde danach neue Details liefert, verwende action='calculate' mit aktualisierten params.]"
        ),
    })


async def coordinator_summarize(session: BlitzschutzSession) -> dict:
    llm = ClaudeLLM(model=HAIKU_MODEL)
    messages = [
        {"role": "system", "content": COORDINATOR_SYSTEM + chr(10) + chr(10) + "WICHTIG FÜR DIESE ANTWORT: Antworte NUR mit der Nachricht an den Kunden als reiner Text (KEIN JSON, KEINE params, KEINE action). Präsentiere das Ergebnis freundlich und professionell auf Deutsch."},
        *session.messages,
    ]
    response = await llm.chat(messages=messages, max_tokens=1024, temperature=0.3)

    text = response.text.strip()
    result = _parse_llm_json(text)

    session.messages.append({"role": "assistant", "content": json.dumps(result, ensure_ascii=False)})
    return result
