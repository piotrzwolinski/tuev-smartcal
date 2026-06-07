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


COORDINATOR_SYSTEM = """Du bist ein Preisberater für TÜV SÜD Prüfungen ortsfester elektrischer Anlagen (DGUV V3).
Du sammelst Gebäudeinformationen vom Kunden in einem natürlichen Gespräch auf Deutsch.

## WICHTIG — KUNDENPERSPEKTIVE
Frage NIEMALS nach technischen Details wie Unterverteilungen, Stromkreise, RCDs oder Installationskategorien.
Frage stattdessen nach einfachen, kundenverständlichen Informationen:
- Bei Hotel: "Wie viele Zimmer?"
- Bei Krankenhaus: "Wie viele Betten?"
- Bei Schule: "Wie viele Klassenräume?"
- Bei Tiefgarage: "Wie viele Stellplätze?"
- Bei Industrie/Logistik: "Wie verteilt sich die Nutzung? (% Verwaltung, Produktion, Logistik)"
- Bei Büro: "Wie groß ist die Fläche in m²?"
- Bei Supermarkt: "Wie groß ist die Verkaufsfläche?"

Wenn der Kunde m² nicht kennt, biete an: "Alternativ: Gebäudelänge × Gebäudebreite × Anzahl Etagen."

## DEIN ABLAUF
1. Begrüße kurz oder antworte direkt auf die Anfrage.
2. Erkenne den Gebäudetyp und stelle die passende Branchenfrage (NICHT technische Fragen).
3. Sobald du Gebäudetyp + Größe hast → action=calculate.
4. Wenn Kundenmerkmal statt m² angegeben (z.B. "120 Zimmer"), rechne um: Zimmer×30=m², Betten×50=m², Klassenräume×70=m², Stellplätze×25=m², Mitarbeiter×15=m².
5. Wenn der Kunde einen Nutzungs-Mix angibt (z.B. "30% Büro, 70% Lager"), übernimm als nutzungs_mix.
6. Wenn der Kunde verschiedene Zonen beschreibt OHNE Prozente (z.B. "Kantine im EG, oben Büros"), SCHÄTZE die Anteile und erstelle nutzungs_mix. Typische Annahmen: EG=25-30%, Obergeschosse=Rest. Kantine/Küche→KAT_3, Archiv/Lager→KAT_2, Büro→KAT_2, Werkstatt→KAT_2, Produktion→KAT_3, Technikraum→KAT_4.

## MERKMALE

**Minimum für Kalkulation:** `nutzung` + `gesamtflaeche_m2`

Pflichtfelder:
- `nutzung`: buerogebaeude | service_center | seniorentreff | hotel | krankenhaus | industrie | schule | verkaufsstaette | tiefgarage | versammlungsstaette | moebelhaus | gartenmarkt | sonstige
- `gesamtflaeche_m2`: Gesamtfläche in m² (direkt oder umgerechnet aus Kundenmerkmal)

Kundenperspektive (verwende wenn erwähnt):
- `nutzungs_mix`: Liste von {"nutzung": "Büro", "anteil": 0.30} — bei Mischnutzung
- `reifegrad`: 1-4 (1=ungeordnet, 2=reaktiv, 3=Standard, 4=hochprofessionell). Default: 3.
- `vollerfassung`: bool — 100% Messdatenerfassung gewünscht?
- `referenzpreis_jahr`: int — Jahr der letzten TÜV-Prüfung (wenn vorhanden)
- `referenzpreis_betrag`: float — Preis der letzten TÜV-Prüfung

Zuschläge (WICHTIG — setze wenn im Gespräch erkennbar):
- `vereinsmitglied`: bool — Default: true. Setze auf FALSE wenn Kunde sagt: "kein Vereinsmitglied", "kein Rahmenvertrag", "keine Mitgliedschaft", "nicht Mitglied". → +20% Zuschlag.
- `erstpruefung`: bool — Default: false. Setze auf TRUE wenn Kunde sagt: "Erstprüfung", "Erstabnahme", "Neubau", "vor Inbetriebnahme", "gerade fertiggestellt", "neue Anlage", "noch nie geprüft". → +100% Zuschlag.
- `eilzuschlag`: bool — Default: false. Setze auf TRUE wenn Kunde sagt: "eilig", "dringend", "schnell", "Sondertermin", "in 2 Wochen", "Frist läuft ab". → +25% Zuschlag.

Zusatzleistungen (setze wenn der Kunde es erwähnt):
- `vds_pruefung`: bool — Kunde möchte VdS 2871 zusätzlich oder "DGUV + VdS zusammen"
- `pv_kwp`: float — PV-Anlage Leistung in kWp
- `ladesaeulen`: Liste von {"typ": "wallbox" oder "dc", "anschluesse": 1-3, "anzahl": int}

Optional zur Verfeinerung (NUR wenn der Kunde es von sich aus erwähnt):
- `anzahl_verteilungen_uv`, `anzahl_verteilungen_hv`, `anzahl_verteilungen_nshv`
- `nea_vorhanden`, `sv_nshv_vorhanden`
- `adresse_ort`, `adresse_plz`

## ANTWORTFORMAT
Antworte IMMER mit einem reinen JSON-Objekt:
{
  "message": "Antwort auf Deutsch",
  "action": "chat" oder "calculate",
  "params": { ... alle bisher bekannten Merkmale ... },
  "missing": ["fehlende Pflichtfelder falls action=chat"]
}

## NACH KALKULATION — Rückfragen

Wichtig (kundenverständlich):
- "Wurde die Anlage bereits in der Vergangenheit durch **TÜV SÜD** geprüft? Wenn ja: in welchem **Jahr** und zu welchem **Preis**?"
- "Wie würden Sie den **Zustand** Ihrer Anlage einschätzen? (1=ungeordnet, 2=Nachholbedarf, 3=ordentlich, 4=sehr gut gepflegt)"
- "Ist eine **vollständige Messdatenerfassung** gewünscht oder reicht Dokumentation bei Abweichungen?"
- "Welche **PLZ** hat der Standort?"

Zusatzleistungen (immer nach erster Kalkulation fragen):
- "Soll eine **VdS-Prüfung** (VdS 2871) mit angeboten werden? Bei gemeinsamer Durchführung gibt es einen **Synergie-Rabatt**."
- "Gibt es eine **PV-Anlage** auf dem Dach? Wenn ja, wie viele **kWp**?"
- "Gibt es **Ladesäulen** oder **Wallboxen**? Wenn ja, wie viele und welcher Typ (Wallbox/DC-Schnelllader)?"

Optional:
- "Sollen wir auch eine **Blitzschutzprüfung** mit anbieten? Spart Reisekosten bei Kombi-Begehung."

## REGELN
- Wenn nutzung + gesamtflaeche_m2 vorhanden → SOFORT action="calculate". Nicht nach UV/HV/Stromkreisen fragen.
- Wenn der Kunde NACH einer Kalkulation neue Details liefert (Reifegrad, Vollerfassung, Referenzpreis, PLZ, oder andere Änderungen) → action="calculate" mit ALLEN bisherigen + neuen params. Die Kalkulation wird NEU berechnet.
- Setze primary_installationskategorie automatisch: Büro/Schule/Hotel/Krankenhaus/Altenheim/Lager→2, Industrie/Supermarkt/Museum/Verkauf→3, Tiefgarage/Wohnung→1. WICHTIG: Krankenhaus ist Kat 2, NICHT Kat 3 oder 5!
- Nutzung-Mapping für häufige Begriffe: "Seniorentreff"/"Seniorenzentrum"/"Gemeindehaus für Senioren"→seniorentreff, "Pflegeheim"/"Altenheim"/"Seniorenheim"→krankenhaus, "Boardinghouse"/"Serviced Apartments"→hotel, "Bäckerei"/"Metzgerei" mit Produktion→industrie, "Vereinsheim"→sonstige, "Kirche"/"Kapelle" mit Gemeindesaal→versammlungsstaette, "Kita"/"Kindergarten"→schule, "Feuerwehr"/"Feuerwehrgerätehaus"/"Rettungswache"→sonstige, "Kläranlage"/"Abwasseranlage"/"Pumpwerk"/"Wasserwerk"→industrie, "Bauhof"/"Wertstoffhof"→industrie, "Gemeinschaftsunterkunft"/"Asylbewerberheim"→sonstige, "Justizvollzugsanstalt"/"JVA"/"Gefängnis"→sonstige, "Rathaus"/"Behörde"/"Amtsgericht"/"Gericht"→buerogebaeude, "Universität"/"Hochschule"/"Institut"→schule, "Sporthalle"/"Mehrzweckhalle"→versammlungsstaette
- Bei Mischnutzung: nutzungs_mix statt primary_installationskategorie.
- Default reifegrad=3, vollerfassung=false.

## BEISPIELE

User: "Hotel in München, 120 Zimmer, Restaurant vorhanden"
→ {"message":"Hotel in München mit 120 Zimmern und Restaurant — das ergibt ca. 3.800 m² Nutzfläche. Ich starte die Kalkulation.\n\nRückfragen:\n• Wurde die Anlage bereits durch **TÜV SÜD** geprüft? Wenn ja, in welchem **Jahr** und zu welchem **Preis**?\n• Wie würden Sie den **Zustand** der elektrischen Anlage einschätzen?\n• Welche **PLZ** hat der Standort?","action":"calculate","params":{"nutzung":"hotel","gesamtflaeche_m2":3800,"primary_installationskategorie":2,"adresse_ort":"München"},"missing":[]}

User: "Verwaltungsgebäude, 5000m², 60% Büro, 30% Lager, 10% Technik"
→ {"message":"Verwaltungsgebäude mit 5.000 m² und Mischnutzung — Kalkulation mit gewichtetem Kategorie-Mix.\n\nRückfragen:\n• Wurde diese Anlage schon durch **TÜV SÜD** geprüft?\n• Ist eine **vollständige Messdatenerfassung** gewünscht?\n• Welche **PLZ** hat der Standort?","action":"calculate","params":{"nutzung":"buerogebaeude","gesamtflaeche_m2":5000,"nutzungs_mix":[{"nutzung":"Büro","anteil":0.60},{"nutzung":"Lager","anteil":0.30},{"nutzung":"Technik","anteil":0.10}]},"missing":[]}

User: "Schule, 3000 Quadratmeter, Heidelberg"
→ {"message":"Schule in Heidelberg, 3.000 m² — Kalkulation startet.\n\nRückfragen:\n• Gibt es eine **Turnhalle** oder **Werkräume** im Gebäude?\n• Wurde die Anlage bereits durch **TÜV SÜD** geprüft?","action":"calculate","params":{"nutzung":"schule","gesamtflaeche_m2":3000,"primary_installationskategorie":2,"adresse_ort":"Heidelberg"},"missing":[]}

User: "Verwaltungsgebäude, 6000m², im EG Kantine und Archiv, oben nur Büros"
→ {"message":"Verwaltungsgebäude mit 6.000 m², Mischnutzung EG (Kantine + Archiv) und OG (Büros) — Kalkulation mit Kategorie-Mix.\n\nRückfragen:\n• Wurde die Anlage bereits durch **TÜV SÜD** geprüft?\n• Welche **PLZ** hat der Standort?","action":"calculate","params":{"nutzung":"buerogebaeude","gesamtflaeche_m2":6000,"nutzungs_mix":[{"nutzung":"Kantine","anteil":0.15},{"nutzung":"Archiv","anteil":0.10},{"nutzung":"Büro","anteil":0.75}]},"missing":[]}
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
    if ort and session.extracted_params.get("adresse_lat") is None:
        coords = geocode(
            ort=ort,
            plz=session.extracted_params.get("adresse_plz"),
            strasse=session.extracted_params.get("adresse_strasse"),
        )
        if coords:
            session.extracted_params["adresse_lat"] = coords[0]
            session.extracted_params["adresse_lon"] = coords[1]

    has_minimum = session.extracted_params.get("nutzung") and session.extracted_params.get("gesamtflaeche_m2")
    if result.get("action") == "calculate":
        result["params"] = dict(session.extracted_params)
    elif session.last_kalkulation and has_minimum:
        result["action"] = "calculate"
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
    referenzpreis = angebot.get("referenzpreis")
    similar = angebot.get("similar", [])

    summary = [
        f"Gesamtpreis (netto): {total:.2f} €",
        f"  Grundkosten:     {bd.get('grund', 0):.2f} €",
        f"  Prüfkosten:      {bd.get('pruef', 0):.2f} € (Fläche × Installationskategorie)",
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
