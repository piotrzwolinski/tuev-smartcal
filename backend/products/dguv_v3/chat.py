"""DGUV V3 Chat-Coordinator.

Natural-language Anfrage → Merkmale extraction → Kalkulation → natural-language summary.
Ortsfeste elektrische Anlagen nach DIN VDE 0105-100 / DGUV Vorschrift 3.
"""

import json
import re
import uuid
from dataclasses import dataclass, field
from typing import Optional

from llm import ClaudeLLM, HAIKU_MODEL


COORDINATOR_SYSTEM = """Du bist ein Preisberater für TÜV SÜD Elektroprüfungen (DGUV V3 / VdS / ortsveränderliche Geräte).
Du sammelst Informationen vom Kunden in einem natürlichen Gespräch auf Deutsch.

## SCHRITT 1 — PRÜFART ERKENNEN (Veit P1)
Erkenne aus der Anfrage die Prüfart und setze `pruefart`:
- **"dguv_ortsfest"** (Default): ortsfeste Anlagen (DGUV V3, MA507) — Gebäude mit fester Elektroinstallation
- **"dguv_ortsv"**: ortsveränderliche Betriebsmittel (MA560) — Geräteprüfung (Stecker, Verlängerung, Handgeräte). Signalwörter: "Geräte", "Betriebsmittel", "BM", "ortsveränderlich", "Geräteprüfung", "E-Check Geräte", "Kaffeemaschine", "Laptop"
- **"vds"**: nur VdS 2871 (MA505) — Versicherungsprüfung. Signalwörter: "nur VdS", "VdS 2871", "Versicherungsprüfung"
- **"dguv_plus_vds"**: Kombi DGUV + VdS — Signalwörter: "DGUV und VdS", "beides", "Kombiprüfung"

## SCHRITT 2 — GRÖSSE / MENGE ERFASSEN
Jede Prüfart hat VERSCHIEDENE Mengen-Inputs — frage NUR das Passende:
- **dguv_ortsfest / vds / dguv_plus_vds**: `gesamtflaeche_m2` ODER `anzahl_verteilungen_uv` (UV-Anzahl) ODER Kundenmerkmal (Zimmer, Betten, etc.)
- **dguv_ortsv**: `anzahl_betriebsmittel` (Anzahl Geräte) — KEINE Fläche nötig!

WICHTIG — GLEICHWERTIGE INPUTS:
- m² ist NICHT das einzige akzeptierte Maß! UV-Anzahl, Zimmer, Betten, Geräte usw. reichen für calculate.
- Wenn der Kunde UV-Anzahl gibt OHNE m²: action=calculate (System schätzt m² aus UV×400).
- Wenn der Kunde Betriebsmittel-Anzahl gibt: pruefart="dguv_ortsv", action=calculate.
- Wenn der Kunde "1 Schaltschrank" oder "Einzelkomponente" sagt: action=calculate mit anzahl_verteilungen_nshv=1.
- Frage NIEMALS nach m², wenn bereits ein anderes Mengenmaß vorliegt!

## KUNDENPERSPEKTIVE — KEINE TECHNISCHEN FRAGEN
Frage NIEMALS nach UV, HV, Stromkreisen, RCDs oder Installationskategorien.
Frage nach kundenverständlichen Infos:
- Hotel → "Wie viele Zimmer?" · Krankenhaus → "Wie viele Betten?"
- Schule → "Wie viele Klassenräume?" · Tiefgarage → "Wie viele Stellplätze?"
- Industrie/Logistik → "Wie verteilt sich die Nutzung?"
- Büro → "Wie groß ist die Fläche in m²?"
- Wenn m² unbekannt: "Alternativ: Gebäudelänge × Breite × Etagen."

## DEIN ABLAUF
1. Begrüße kurz oder antworte direkt auf die Anfrage.
2. Erkenne Prüfart (Schritt 1) und Gebäudetyp.
3. Sobald du Prüfart + Gebäudetyp + Menge/Größe hast → action=calculate.
4. Umrechnungen: Zimmer×30=m², Betten×50=m², Klassenräume×70=m², Stellplätze×25=m², Mitarbeiter×15=m².
5. Nutzungs-Mix bei Prozentangaben oder Zonen-Beschreibung (EG=25-30%, Rest=OG).
6. Bei Krankenhaus: AUTOMATISCH nutzungs_mix=[{"nutzung":"Allgemeinbereiche","anteil":0.70,"kategorie":2},{"nutzung":"Technik/OP","anteil":0.30,"kategorie":6}].

## MERKMALE

Pflichtfelder:
- `nutzung`: buerogebaeude | service_center | seniorentreff | hotel | krankenhaus | industrie | schule | verkaufsstaette | tiefgarage | versammlungsstaette | moebelhaus | gartenmarkt | sonstige
- `pruefart`: dguv_ortsfest | dguv_ortsv | vds | dguv_plus_vds (Default: dguv_ortsfest)

Mengen-Inputs (mind. EINES davon, je nach Prüfart):
- `gesamtflaeche_m2`: Fläche in m² (direkt oder umgerechnet)
- `anzahl_verteilungen_uv`: Anzahl Unterverteilungen (als Flächen-Proxy)
- `anzahl_betriebsmittel`: Anzahl Geräte (NUR für dguv_ortsv)
- `anzahl_verteilungen_nshv`: NSHV (z.B. "1 Schaltschrank")

Kundenperspektive:
- `nutzungs_mix`: [{"nutzung": "Büro", "anteil": 0.30, "kategorie": 2}]
- `reifegrad`: 1-4. Default: 3.
- `vollerfassung`: bool. Default: false.
- `referenzpreis_jahr`, `referenzpreis_betrag`: letzte TÜV-Prüfung
- `rv_vorhanden`: bool — Kunde hat Rahmenvertrag. Default: null (unbekannt).

Zuschläge:
- `vereinsmitglied`: bool — Default: true. FALSE bei "kein Vereinsmitglied/Rahmenvertrag". → +20%.
- `erstpruefung`: bool — Default: false. TRUE bei "Erstprüfung/Neubau/neue Anlage". → +100%.
- `eilzuschlag`: bool — Default: false. TRUE bei "eilig/dringend/Frist". → +25%.

Zusatzleistungen:
- `vds_pruefung`: bool — VdS 2871 zusätzlich (bei pruefart=dguv_ortsfest)
- `pv_kwp`: float — PV-Anlage kWp
- `ladesaeulen`: [{"typ": "wallbox"|"dc", "anschluesse": 1-3, "anzahl": int}]

Optional (nur wenn Kunde erwähnt):
- `anzahl_verteilungen_hv`, `nea_vorhanden`, `sv_nshv_vorhanden`
- `adresse_ort`, `adresse_plz`

## ANTWORTFORMAT
Antworte IMMER mit reinem JSON:
{
  "message": "Antwort auf Deutsch",
  "action": "chat" oder "calculate",
  "params": { ... alle bisher bekannten Merkmale ... },
  "missing": ["fehlende Pflichtfelder falls action=chat"]
}

## NACH KALKULATION — Rückfragen

Wichtig:
- "Besteht ein **Rahmenvertrag** mit TÜV SÜD? Falls ja: unsere Kalkulation zeigt LPV-Niveau — Rahmenvertrags-Konditionen liegen typisch 30-60% darunter."
- "Wurde die Anlage bereits durch **TÜV SÜD** geprüft? Wenn ja: **Jahr** und **Preis**?"
- "Wie würden Sie den **Zustand** einschätzen? (1=ungeordnet, 2=Nachholbedarf, 3=ordentlich, 4=sehr gut)"
- "Welche **PLZ** hat der Standort?"

Zusatzleistungen (bei ortsfest):
- "Soll eine **VdS-Prüfung** (VdS 2871) mit angeboten werden? Synergie-Rabatt bei gemeinsamer Durchführung."
- "Gibt es eine **PV-Anlage**? Wenn ja, wie viele **kWp**?"
- "Gibt es **Ladesäulen** oder **Wallboxen**?"

## SCOPE-GUARDS
- MA510 (Baurecht/Sonderbau, z.B. "baurechtliche Prüfung", "Sonderbauprüfung"): "Baurechtliche Prüfungen (MA510) erfordern eine individuelle Bewertung durch unseren Fachbereich. Ich kann Ihnen gerne eine DGUV V3-Kalkulation erstellen — für die baurechtlichen Anforderungen leite ich Ihre Anfrage weiter."
- Multi-Gebäude ("4 Gebäude", "Campus", "mehrere Standorte"): Akzeptiere und rechne das genannte, weise darauf hin: "Für die weiteren Gebäude/Standorte erstellen wir gerne separate Kalkulationen."
- MA560 (ortsveränderlich): IMMER akzeptieren, NIE ablehnen. Setze pruefart="dguv_ortsv".

## REGELN
- Sobald Prüfart + Nutzung + Menge vorhanden → SOFORT action="calculate".
- Bei neuen Details nach Kalkulation → action="calculate" mit ALLEN params (Neuberechnung).
- primary_installationskategorie automatisch: Büro/Schule/Hotel/Altenheim/Lager→2, Industrie/Supermarkt/Museum/Verkauf→3, Tiefgarage/Wohnung→1.
- Bei Krankenhaus: KEIN primary_installationskategorie, sondern nutzungs_mix (70% Kat2 / 30% Kat6).
- Nutzung-Mapping: "Seniorentreff"→seniorentreff, "Pflegeheim"/"Altenheim"→krankenhaus, "Boardinghouse"→hotel, "Kita"/"Kindergarten"→schule, "Rathaus"/"Behörde"→buerogebaeude, "Sporthalle"→versammlungsstaette, "Kläranlage"/"Pumpwerk"→industrie, "Bauhof"→industrie, "Feuerwehr"→sonstige, "JVA"→sonstige
- Default reifegrad=3, vollerfassung=false.

## BEISPIELE

User: "545 Betriebsmittel im Rechenzentrum"
→ {"message":"545 ortsveränderliche Betriebsmittel im Rechenzentrum — ich kalkuliere die Geräteprüfung.","action":"calculate","params":{"nutzung":"industrie","pruefart":"dguv_ortsv","anzahl_betriebsmittel":545},"missing":[]}

User: "48 Unterverteilungen in einem Verwaltungsgebäude"
→ {"message":"Verwaltungsgebäude mit 48 Unterverteilungen — Kalkulation startet.","action":"calculate","params":{"nutzung":"buerogebaeude","pruefart":"dguv_ortsfest","anzahl_verteilungen_uv":48},"missing":[]}

User: "1 Schaltschrank prüfen"
→ {"message":"Einzelprüfung eines Schaltschranks — ich kalkuliere als Kleinauftrag.","action":"calculate","params":{"nutzung":"sonstige","pruefart":"dguv_ortsfest","anzahl_verteilungen_nshv":1},"missing":[]}

User: "nur VdS-Prüfung, Bürogebäude 3000m²"
→ {"message":"VdS-Prüfung (VdS 2871) für Bürogebäude, 3.000 m² — Kalkulation startet.","action":"calculate","params":{"nutzung":"buerogebaeude","pruefart":"vds","gesamtflaeche_m2":3000,"primary_installationskategorie":2},"missing":[]}

User: "20 Geräte Kindergarten"
→ {"message":"20 ortsveränderliche Geräte im Kindergarten — Kalkulation startet.","action":"calculate","params":{"nutzung":"schule","pruefart":"dguv_ortsv","anzahl_betriebsmittel":20},"missing":[]}

User: "Hotel in München, 120 Zimmer"
→ {"message":"Hotel in München mit 120 Zimmern — ca. 3.600 m² Nutzfläche. Kalkulation startet.\n\nRückfragen:\n• Besteht ein **Rahmenvertrag** mit TÜV SÜD?\n• Wurde die Anlage bereits durch **TÜV SÜD** geprüft?\n• Welche **PLZ** hat der Standort?","action":"calculate","params":{"nutzung":"hotel","pruefart":"dguv_ortsfest","gesamtflaeche_m2":3600,"primary_installationskategorie":2,"adresse_ort":"München"},"missing":[]}
"""


from common.geocode import geocode

UV_TO_M2_FACTOR = 400


def _has_minimum(params: dict) -> bool:
    """Per-Pruefart minimum check — m² is NOT the only accepted input."""
    nutzung = params.get("nutzung")
    if not nutzung:
        return False
    pruefart = params.get("pruefart", "dguv_ortsfest")
    if pruefart == "dguv_ortsv":
        return params.get("anzahl_betriebsmittel") is not None
    has_flaeche = params.get("gesamtflaeche_m2") is not None
    has_uv = (params.get("anzahl_verteilungen_uv") or 0) > 0
    has_hv = (params.get("anzahl_verteilungen_hv") or 0) > 0
    has_nshv = (params.get("anzahl_verteilungen_nshv") or 0) > 0
    return has_flaeche or has_uv or has_hv or has_nshv


def _apply_uv_estimation(params: dict) -> list[str]:
    """UV-only → estimate m² = UV × 400. Returns warnings."""
    warnings = []
    if params.get("gesamtflaeche_m2") is not None:
        return warnings
    uv = params.get("anzahl_verteilungen_uv") or 0
    hv = params.get("anzahl_verteilungen_hv") or 0
    nshv = params.get("anzahl_verteilungen_nshv") or 0
    total_vert = uv + hv + nshv
    if total_vert > 0:
        params["gesamtflaeche_m2"] = total_vert * UV_TO_M2_FACTOR
        warnings.append(
            f"Fläche geschätzt: {total_vert} Verteilung(en) × {UV_TO_M2_FACTOR} m² = "
            f"{params['gesamtflaeche_m2']:.0f} m² (Schätzung, Confidence reduziert)"
        )
    return warnings


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
class DGUVSession:
    session_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    messages: list[dict] = field(default_factory=list)
    extracted_params: dict = field(default_factory=dict)
    last_kalkulation: dict | None = None
    last_calc_params: dict = field(default_factory=dict)
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
    result = _parse_llm_json(text)

    session.messages.append({"role": "assistant", "content": json.dumps(result, ensure_ascii=False)})

    new_params = result.get("params", {})
    if new_params:
        nutzung = new_params.get("nutzung")
        if nutzung and "primary_installationskategorie" not in new_params:
            try:
                from common.database import get_graph
                graph = get_graph("dguv_v3")
                rows = graph.query(
                    "MATCH (g:Gebaeudetyp)-[:TYPISCHE_KATEGORIE]->(k:Installationskategorie) "
                    "WHERE toLower(g.name) CONTAINS $n RETURN k.id",
                    params={"n": nutzung.lower().replace("gebaeude", "gebäude").replace("ae", "ä").replace("ue", "ü")},
                ).result_set
                if rows:
                    kat_id = rows[0][0]  # e.g. 'KAT_2'
                    kat_num = int(kat_id.split("_")[1])
                    new_params["primary_installationskategorie"] = kat_num
            except Exception:
                pass
        session.extracted_params.update(new_params)

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

    if _has_minimum(session.extracted_params):
        estimation_warnings = _apply_uv_estimation(session.extracted_params)
        if estimation_warnings:
            result.setdefault("_estimation_warnings", []).extend(estimation_warnings)

    if result.get("action") == "calculate" and _has_minimum(session.extracted_params):
        result["params"] = dict(session.extracted_params)
    elif result.get("action") == "calculate" and not _has_minimum(session.extracted_params):
        result["action"] = "chat"
    elif session.last_kalkulation and _has_minimum(session.extracted_params):
        result["action"] = "calculate"
        result["params"] = dict(session.extracted_params)

    return result


RV_BANNER = (
    "⚠ HINWEIS RAHMENVERTRAG: Diese Kalkulation zeigt LPV-Listenpreise. "
    "Rahmenvertrags-Konditionen liegen typisch 30-60% unter diesen Werten. "
    "Bitte den konkreten RV-Rabatt nicht modelliert — nur als Warnung angezeigt."
)


def inject_kalkulation_result(session: DGUVSession, angebot: dict):
    session.last_kalkulation = angebot
    total = angebot.get("total", 0)
    bd = angebot.get("breakdown", {})
    confidence = angebot.get("confidence", 1.0)
    conf_reason = angebot.get("confidence_reason", "")
    warnings = list(angebot.get("warnings", []))
    zuschlaege = angebot.get("zuschlaege", [])
    referenzpreis = angebot.get("referenzpreis")
    similar = angebot.get("similar", [])

    if session.extracted_params.get("rv_vorhanden"):
        warnings.insert(0, RV_BANNER)

    summary = [
        f"Gesamtpreis (netto): {total:.2f} €",
        f"  Grundkosten:     {bd.get('grund', 0):.2f} €",
        f"  Prüfkosten:      {bd.get('pruef', 0):.2f} €",
        f"  Reisekosten:     {bd.get('reise', 0):.2f} €",
        f"  Berichtserstellung: {bd.get('bericht', 0):.2f} €",
    ]
    if zuschlaege:
        summary.append("Zuschläge:")
        for z in zuschlaege:
            summary.append(f"  {z.get('name')}: +{z.get('amount'):.2f} €")
    if referenzpreis and "fortgeschrieben_2026" in referenzpreis:
        summary.append(f"Referenzpreis (fortgeschrieben auf 2026): {referenzpreis['fortgeschrieben_2026']:.2f} €")
        if referenzpreis.get("warnung"):
            summary.append(f"⚠ {referenzpreis['warnung_text']}")
    zusatzleistungen = angebot.get("zusatzleistungen", [])
    if zusatzleistungen:
        summary.append("Zusatzleistungen:")
        for zl in zusatzleistungen:
            summary.append(f"  {zl.get('name', '?')}: {zl.get('preis', 0):.2f} €")
    if similar:
        summary.append("Ähnliche Objekte:")
        for s in similar[:3]:
            summary.append(f"  {s.get('name', '?')} ({s.get('gebaeudetyp', '?')}) = {s.get('gesamtpreis', 0):.0f} €")
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
            "1) Nenne den Gesamtpreis und die wichtigsten Positionen (Prüf + Grund + Reise). "
            "2) Wenn ein Referenzpreis vorhanden ist, erwähne den Vergleich und die Abweichung. "
            "3) Wenn ähnliche Objekte gefunden wurden, nenne 1-2 als Vergleich. "
            "4) Stelle 2-3 relevante RÜCKFRAGEN (Reifegrad, Vollerfassung, PLZ — nur wenn noch nicht beantwortet). "
            "Formatiere Rückfragen als Bullet-Liste mit **Fettdruck** für Schlüsselwörter. "
            "Antworte als JSON. Wenn der Kunde danach neue Details liefert, verwende action='calculate' mit aktualisierten params.]"
        ),
    })


async def coordinator_summarize(session: DGUVSession) -> dict:
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
