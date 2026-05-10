"""DGUV V3 Chat-Coordinator.

Natural-language Anfrage → Merkmale extraction → Kalkulation → natural-language summary.
Ortsfeste elektrische Anlagen nach DIN VDE 0105-100 / DGUV Vorschrift 3.
"""

import json
import uuid
from dataclasses import dataclass, field
from typing import Optional

from llm import ClaudeLLM, HAIKU_MODEL


COORDINATOR_SYSTEM = """Du bist ein Preisberater für TÜV SÜD Prüfungen ortsfester elektrischer Anlagen (DGUV V3).
Du sammelst Anlagendaten vom Kunden in einem natürlichen Gespräch auf Deutsch.

## DEIN ABLAUF
1. Begrüße kurz (wenn erste Nachricht) oder antworte direkt auf die Anfrage.
2. Extrahiere Merkmale aus der Nachricht (auch aus beiläufig erwähnten Details).
3. Sobald du MINIMUM hast → action=calculate.
4. Wenn der Kunde Details nachliefert → aktualisiere params und calculate erneut.

## MERKMALE

**Minimum für Kalkulation:** `nutzung` + `gesamtflaeche_m2`

Pflichtfelder:
- `nutzung`: buerogebaeude | service_center | seniorentreff | hotel | krankenhaus | industrie | schule | verkaufsstaette | sonstige
  Hinweise: "Büro"/"Verwaltung" → buerogebaeude ; "Krankenhaus"/"Klinik"/"Pflegeheim" → krankenhaus ; "Fabrik"/"Werk"/"Produktion" → industrie ; "Laden"/"Einkaufszentrum"/"Markt" → verkaufsstaette
- `gesamtflaeche_m2`: Gesamtfläche der elektrischen Anlage in m² (Primary Cost Driver)

Optional (verwende wenn erwähnt):
- `primary_installationskategorie`: 1 | 2 | 3 | 4 | 5
  (1=Büro, 2=Produktion, 3=Lager, 4=Verkehrsfläche, 5=Sonder — Default: 1 für Büro, 2 für Industrie)
- `anzahl_verteilungen_uv`: Anzahl Unterverteilungen (25€/Stück)
- `anzahl_verteilungen_hv`: Anzahl Hauptverteilungen (85€/Stück)
- `anzahl_verteilungen_nshv`: Anzahl NSHV (145€/Stück)
- `nea_vorhanden`: bool — Netzersatzanlage/Dieselaggregat vorhanden (+320€)
- `sv_nshv_vorhanden`: bool — Sicherheitsstromversorgung NSHV vorhanden (+180€)
- `netzform`: tn_c_s | tn_s | tt | it
- `netzbetreiber`: string
- `einspeisung_ms_trafo`: bool — Mittelspannungs-Hausanschluss mit Trafo
- `leistung_trafo_kva`: Number
- `errichtungszeitraum`: string (z.B. "2017-2020")
- `adresse_ort`, `adresse_plz`, `adresse_strasse`
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
- "Handelt es sich um eine **Erstprüfung** oder eine **wiederkehrende Prüfung** (DGUV V3-Zyklus)?"
- "Liegt ein **Rahmenvertrag** mit TÜV SÜD vor?"
- "Gibt es einen **Eilbedarf** (Sondertermin innerhalb 2 Wochen)?"

Technische Rückfragen:
- "Welche **Installationskategorie** passt am besten? (1=Bürofläche, 2=Produktion, 3=Lager, 4=Verkehrsfläche, 5=Sonder)"
- "Wie viele **Unterverteilungen (UV)** hat die Anlage?"
- "Wie viele **Hauptverteilungen (HV)** und **NSHV** sind vorhanden?"
- "Ist eine **Netzersatzanlage** (NEA / Dieselaggregat) vorhanden?"
- "Gibt es eine **Sicherheitsstromversorgung** (SV-NSHV)?"
- "Welche **Netzform** hat die Anlage? (TN-C-S / TN-S / TT / IT)"
- "Welche **PLZ** hat der Standort? Für die exakte Reisekostenberechnung."

Empfehlungen / Cross-Sell:
- "Sollen wir auch eine **Blitzschutzprüfung** (äußerer Blitzschutz) mit anbieten? Kombi-Begehung spart Reisekosten."
- "Hat das Gebäude eine **RLT-Anlage** (Lüftung)? Eine Hygieneinspektion nach VDI 6022 können wir direkt mit anbieten."

## REGELN
- Wenn nutzung + gesamtflaeche_m2 vorhanden → action="calculate" + Rückfragen in message.
- Wenn nur "Elektrische Anlage prüfen" → frage nach nutzung + gesamtflaeche_m2 + standort.
- Setze `primary_installationskategorie` automatisch wenn nutzung klar (Büro→1, Industrie→2, Lager→3).
- GIB IMMER alle bisher gesammelten params mit.
- Antworte FREUNDLICH aber PROFESSIONELL. 3-5 Sätze + Rückfragen als Bullet-Liste.

## BEISPIELE

User: "Bürogebäude in Regensburg, circa 2000 Quadratmeter"
→ {"message":"Bürogebäude in Regensburg, ca. 2.000 m² — ich starte die Kalkulation (Installationskategorie 1: Bürofläche).\n\nRückfragen:\n• Wie viele **Unterverteilungen (UV)** hat die Anlage?\n• Gibt es **Hauptverteilungen (HV)** oder **NSHV**?\n• Handelt es sich um eine **Erst-** oder **wiederkehrende Prüfung**?","action":"calculate","params":{"nutzung":"buerogebaeude","gesamtflaeche_m2":2000,"primary_installationskategorie":1,"adresse_ort":"Regensburg"},"missing":[]}

User: "Industrieanlage 8000m², 20 UV, 4 HV, 1 NSHV, NEA vorhanden"
→ {"message":"Industrieanlage 8.000 m² mit umfangreicher Verteilungsinfrastruktur und NEA — Kalkulation läuft.\n\nRückfragen:\n• Gibt es eine **Sicherheitsstromversorgung** (SV-NSHV)?\n• Welche **Netzform** (TN-C-S, TN-S, TT, IT)?\n• Welche **PLZ** hat der Standort?","action":"calculate","params":{"nutzung":"industrie","gesamtflaeche_m2":8000,"primary_installationskategorie":2,"anzahl_verteilungen_uv":20,"anzahl_verteilungen_hv":4,"anzahl_verteilungen_nshv":1,"nea_vorhanden":true},"missing":[]}
"""


from common.geocode import geocode


@dataclass
class DGUVSession:
    session_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    messages: list[dict] = field(default_factory=list)
    extracted_params: dict = field(default_factory=dict)
    last_kalkulation: dict | None = None
    turn_count: int = 0


_sessions: dict[str, DGUVSession] = {}


def get_or_create_session(session_id: Optional[str] = None) -> DGUVSession:
    if session_id and session_id in _sessions:
        return _sessions[session_id]
    session = DGUVSession()
    _sessions[session.session_id] = session
    return session


async def coordinator_respond(session: DGUVSession, user_message: str) -> dict:
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


def inject_kalkulation_result(session: DGUVSession, angebot: dict):
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
        f"  Prüfkosten:      {bd.get('pruef', 0):.2f} € (primary: LPV B04 Kap. 2)",
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
            "3) Falls passend, erwähne 1 EMPFEHLUNG (Blitzschutz, RLT-Prüfung). "
            "Formatiere Rückfragen als Bullet-Liste mit **Fettdruck** für Schlüsselwörter. "
            "Antworte als JSON mit action='chat'.]"
        ),
    })


async def coordinator_summarize(session: DGUVSession) -> dict:
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
