"""LLM-as-Judge evaluation module for DGUV V3 E2E tests.

User-LLM (Sonnet): generates realistic customer messages from persona descriptions.
Judge-LLM (Sonnet): evaluates system output against HARD FACTS from pricing rules.
"""

import json
import asyncio
from dataclasses import dataclass, field

from llm import ClaudeLLM, MODEL
from scripts.e2e_scenarios import E2EScenario

SONNET_MODEL = "claude-sonnet-4-5-20250929"

JUDGE_DIMENSIONS = [
    "extraction",
    "pricing",
    "conversation",
    "trace",
    "kalibrierung",
    "completeness",
]


@dataclass
class JudgeVerdict:
    scenario_id: str
    scores: dict[str, int] = field(default_factory=dict)
    reasoning: dict[str, str] = field(default_factory=dict)
    avg_score: float = 0.0
    passed: bool = False
    error: str = ""

    def to_dict(self) -> dict:
        return {
            "scenario_id": self.scenario_id,
            "scores": self.scores,
            "reasoning": self.reasoning,
            "avg_score": self.avg_score,
            "passed": self.passed,
            "error": self.error,
        }


USER_LLM_SYSTEM = """Du bist ein Kunde, der eine Prüfung ortsfester elektrischer Anlagen bei TÜV SÜD anfragen möchte.
Du sprichst natürlich und realistisch auf Deutsch — wie ein echter Kunde, der zum ersten Mal anruft.

## DEINE ROLLE
Du spielst die folgende Person:
{persona}

## DEIN GEBÄUDE
{gebaeude}

## WAS DU WEISST
{wissen}

## WAS DU WILLST
{absicht}

## REGELN
- Sprich natürlich, wie ein echter Mensch. Keine perfekten Aufzählungen.
- Gib NICHT alle Infos auf einmal — gib sie stückweise, wie im echten Gespräch.
- Wenn du etwas nicht weißt (z.B. m²), sag es ehrlich oder schätze grob.
- Beantworte Rückfragen des Systems mit den dir bekannten Infos.
- WICHTIG: Wenn das System dir Fragen stellt (PLZ, Zustand der Anlage, frühere Prüfung, etc.), beantworte sie ZUERST mit den Infos aus deiner Rolle, BEVOR du [DONE] sagst.
- Du kennst KEINE technischen Details wie Installationskategorien oder Unterverteilungen.
- Halte dich an die Fakten aus deiner Rolle — erfinde nichts dazu.
- Antworte in 1-3 Sätzen pro Nachricht, nicht in langen Absätzen.
- Sage [DONE] NUR wenn: (1) du ein Angebot bekommen hast UND (2) keine unbeantworteten Fragen vom System offen sind.

## KONVERSATION BISHER
{conversation_so_far}

## AKTUELLE TURN-NUMMER
Turn {turn_number} von maximal {max_turns}.
Bei Turn {max_turns}: Beantworte noch offene Fragen und sage dann [DONE].
"""


JUDGE_SYSTEM = """Du bist ein Prüfer, der ein Kalkulationssystem für DGUV V3 Prüfungen anhand HARTER FAKTEN bewertet.
Du MUSST deine Bewertung auf die unten stehenden Preisregeln stützen — NICHT auf Bauchgefühl.

## PREISREGELN (GROUND TRUTH)

Das Angebot hat 4 SEPARATE Blöcke im Breakdown. Du MUSST jeden Block einzeln prüfen.

### BLOCK 1: breakdown.grund = Grundkosten
Grundkosten = Pauschale + Prüfmittel + Tagegeld (NICHT 250€ — das ist der Prüfkosten-Grundpreis!)
- Pauschale Auftragsanlage: 256,00 €
- Prüfmittel: 49,00 € × Prüftage
- Tagegeld: 0€ (<6h), 6€ (6-8h), 25€ (8-14h), 30€ (14-24h)
- Prüftage: ≤500m²→0,5d, ≤2000m²→1d, ≤5000m²→2d, >5000m²→m²/2500
Beispiel 5.400m²: Tage=2,16 → 256 + 49×2,16 + 25 = 387€
Beispiel 1.200m²: Tage=1,0 → 256 + 49×1,0 + 6 = 311€
Beispiel 350m²: Tage=0,5 → 256 + 49×0,5 + 0 = 281€

### BLOCK 2: breakdown.pruef = Prüfkosten
Prüfkosten = Grundpreis_Anlage (250€) + (Fläche_m²/10) × Kat-Rate
WICHTIG: Die 250€ Grundpreis_Anlage sind IN den Prüfkosten, NICHT in Grundkosten!
Danach × Reifegrad-Faktor × Vollerfassungs-Faktor (falls aktiv).

Kat-Rates (€/10m²):
- Kat 1: 1,00 (Tiefgarage, Wohnung, Freiflächen)
- Kat 2: 3,10 (Büro, Schule, Hotel, Krankenhaus, Lager, Altenheim)
- Kat 3: 5,00 (Supermarkt, Produktion, Museum, Verkaufsfläche, Versammlungsraum)
- Kat 4: 5,40 (Technikräume, Reinraum)
- Kat 5: 5,40 (OP, Labor)
- Kat 6: 6,00 (NSHV, Trafo)

Verteilungszuschläge (IN Prüfkosten, pro Stück): UV=25€, HV=85€, NSHV=145€
Sonderzuschläge (IN Prüfkosten): NEA=320€, SV-NSHV=180€
Reifegrad-Faktor: RG1=×1,25, RG2=×1,25, RG3=×1,00, RG4=×0,80
Vollerfassung: ×1,30

Beispiel Büro 4.500m² Kat2 RG3: 250 + (4500/10)×3,10 = 250+1395 = 1.645€
Beispiel Hotel 5.400m² Kat2: 250 + (5400/10)×3,10 = 250+1674 = 1.924€
Beispiel Industrie 8.000m² Kat3: 250 + (8000/10)×5,00 = 250+4000 = 4.250€

### BLOCK 3: breakdown.reise = Reisekosten
Abhängig von PLZ → nächste Niederlassung. Enthält km-Pauschale + Reisezeit.

### BLOCK 4: breakdown.bericht = Berichterstellung
Abhängig von Komplexität. Klein ~150€, Standard ~200€, Komplex ~400€.

### TOTAL
Total = (Grund + Prüf + Reise + Bericht + Zusatzleistungen) × Zuschlagsfaktoren

### Zuschläge (auf Subtotal NACH allen 4 Blöcken + Zusatzleistungen)
- Nicht-Vereinsmitglied: +20%
- Eilzuschlag: +25%
- Erstprüfung: +100%

### Typische Kategorie pro Nutzung
buerogebaeude→2, service_center→2, seniorentreff→2, hotel→2, krankenhaus→2 (NICHT 5!),
industrie→3, schule→2, verkaufsstaette→3, tiefgarage→1, versammlungsstaette→3,
moebelhaus→3, gartenmarkt→3

### Umrechnungen (Kundenmerkmal → m²)
Zimmer×30, Betten×50, Klassenräume×70, Stellplätze×25, Mitarbeiter×15, Sitzplätze×3

### Referenzpreis-Fortschreibung (Preissteigerung seit Jahr X bis 2026)
2020: +28,2%, 2021: +24,4%, 2022: +20,8%, 2023: +14,8%, 2024: +8,3%, 2025: +5,5%
Warnung wenn Abweichung >20% vom fortgeschriebenen Referenzpreis

### DEKA Ground Truth (3 Bürogebäude München, Großkunde)
- Barthstr 12-22: 8.000 m², VdS, Preis 9.733 € (→ ~11,84 €/10m²)
- Landsberger 84-90: 12.000 m², kombiniert, Preis 15.078 € (→ ~12,36 €/10m²)
- Landsberger 94-98: 4.000 m², DGUV, Preis 5.255 € (→ ~12,51 €/10m²)
HINWEIS: DEKA-Preise sind Großkundenpreise und 3-4× höher als Kalkulationshilfen (3,10 €/10m²).
Das System nutzt die Kalkulationshilfen-Rate, NICHT die DEKA-Rate. Das ist KEIN Fehler.

### Nutzung-Enums (gültige Werte)
buerogebaeude, service_center, seniorentreff, hotel, krankenhaus, industrie,
schule, verkaufsstaette, tiefgarage, versammlungsstaette, moebelhaus, gartenmarkt, sonstige

## SCENARIO
{scenario_description}

## ERWARTETE ERGEBNISSE
{expected}

## TRICKY ASPECT
{tricky_aspect}

## KONVERSATION
{conversation}

## LETZTES ANGEBOT (falls vorhanden)
{angebot}

## PROVENANCE / TRACE (Graph-Reasoning-Schritte)
{provenance}

## BEWERTUNGSDIMENSIONEN — FAKTENBASIERT

1. **extraction**: Prüfe EXAKT:
   - Wurde die richtige `nutzung` aus dem Enum gewählt? (z.B. "Pflegeheim" → krankenhaus ODER seniorentreff, "Kita" → schule)
   - Liegt `gesamtflaeche_m2` im erwarteten Bereich? Bei Umrechnungen: stimmt die Formel? (z.B. 180 Zimmer × 30 = 5.400 m²)
   - Stimmt `primary_installationskategorie` mit der Nutzung-Tabelle überein?

2. **pricing**: RECHNE NACH anhand der 4-Block-Regeln:
   - breakdown.grund: Pauschale(256) + Prüfmittel(49×Tage) + Tagegeld. Stimmt?
   - breakdown.pruef: 250 + (m²/10) × Kat-Rate + Verteilungszuschläge. Stimmt?
   - Modifikatoren auf Prüfkosten korrekt? (Reifegrad-Faktor, Vollerfassung ×1,30)
   - Zuschläge auf Subtotal korrekt? (Erst +100%, Eil +25%, Nicht-Mitglied +20%)
   - ACHTUNG: breakdown.grund (≈280-400€) und Grundpreis_Anlage (250€ in Prüfkosten) sind VERSCHIEDENE Dinge!
   - SONDERFALL: Wenn Pflichtfelder (m²) fehlen und KEIN Angebot erstellt wurde, ist das KORREKT → gib 4/5 wenn System richtig nachgefragt hat statt zu raten.

3. **conversation**: Prüfe:
   - System fragt auf Deutsch, in Kundenperspektive (Zimmer, m², nicht UV/Stromkreise)?
   - Bei fehlenden Pflichtfeldern (nutzung oder m²): System fragt nach, rechnet NICHT?
   - Bei Korrekturen: System aktualisiert und rechnet neu?
   - Keine technischen Fragen an Kunden (Installationskategorie, RCD, Netzform)?

4. **trace**: Prüfe ob vorhanden:
   - Grundkosten-Step mit Wert ~280-400€ (Pauschale 256€ + Prüfmittel + Tagegeld)
   - Prüfkosten-Step mit Fläche×Kat Berechnung
   - Reisekosten-Step
   - Bericht-Step
   - Node-IDs / Referenzen zu Graph-Knoten

5. **kalibrierung**: Prüfe:
   - Bei Bürogebäude: Gibt es einen Kalibrierungshinweis mit DEKA-Referenz? (Kalkulationshilfen 3,1€/10m² vs. Marktdaten ~12€/10m²)
   - Bei anderen Gebäudetypen: Keine DEKA-Kalibrierung erwartet → 3 Punkte wenn kein Hinweis, 4+ wenn trotzdem sinnvoller Hinweis

6. **completeness**: Prüfe ob ALLE im Scenario genannten Features verarbeitet wurden:
   - VdS als Zusatzleistung mit eigenem Preis?
   - PV mit kWp und DIN/VdS Norm-Preis?
   - Ladesäulen mit Typ (Wallbox/DC) und Stückzahl?
   - Referenzpreis mit Fortschreibung und Vergleich?
   - Reifegrad als Faktor angewendet?
   - Vollerfassung als Faktor angewendet?
   - Wenn Scenario keine Extras hat: Basiskalkulation vollständig?

## ANTWORTFORMAT
Antworte als reines JSON mit "scores" (0-5 pro Dimension) und "reasoning" (Begründung pro Dimension).
Dimensionen: extraction, pricing, conversation, trace, kalibrierung, completeness.
Begründung MUSS konkrete Zahlen enthalten (z.B. "Erwartet: 250 + 4500/10 × 3.10 = 1645€, System: 1395€ → Differenz -15%").
"""


def _parse_json(text: str) -> dict:
    text = text.strip()
    if "```json" in text:
        text = text.split("```json")[1].split("```")[0].strip()
    elif "```" in text:
        text = text.split("```")[1].split("```")[0].strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        import re
        match = re.search(r'\{[\s\S]*\}', text)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                pass
    return {}


async def user_llm_generate(
    scenario: E2EScenario,
    conversation: list[dict],
    turn_idx: int,
    system_response: str = "",
) -> str | None:
    """Generate a realistic customer message using Sonnet."""
    conv_text = ""
    for turn in conversation:
        conv_text += f"Kunde: {turn['user']}\n"
        msg = turn.get("coordinator", {}).get("message", "")
        if turn.get("summary"):
            msg = turn["summary"].get("message", msg)
        conv_text += f"System: {msg}\n\n"

    if system_response:
        conv_text += f"System: {system_response}\n\n"

    prompt = (USER_LLM_SYSTEM
        .replace("{persona}", scenario.persona)
        .replace("{gebaeude}", scenario.gebaeude)
        .replace("{wissen}", scenario.wissen)
        .replace("{absicht}", scenario.absicht)
        .replace("{conversation_so_far}", conv_text if conv_text else "(Konversation startet jetzt)")
        .replace("{turn_number}", str(turn_idx + 1))
        .replace("{max_turns}", str(scenario.max_turns))
    )

    llm = ClaudeLLM(model=SONNET_MODEL)
    response = await llm.chat(
        messages=[
            {"role": "system", "content": prompt},
            {"role": "user", "content": "Schreibe deine nächste Nachricht als Kunde."},
        ],
        max_tokens=256,
        temperature=0.7,
    )

    text = response.text.strip()
    if "[DONE]" in text:
        return None
    return text


async def judge_evaluate(
    scenario: E2EScenario,
    conversation: list[dict],
    angebote: list[dict],
    provenance: list[dict],
) -> JudgeVerdict:
    """Have Judge-LLM (Sonnet) evaluate the conversation against hard pricing facts."""
    verdict = JudgeVerdict(scenario_id=scenario.id)

    conv_text = ""
    for turn in conversation:
        conv_text += f"Kunde: {turn['user']}\n"
        coord = turn.get("coordinator", {})
        if coord.get("action") == "calculate":
            conv_text += f"System: [Kalkulation getriggert mit params: {json.dumps(coord.get('params', {}), ensure_ascii=False)[:500]}]\n"
        else:
            conv_text += f"System: {coord.get('message', '')}\n"
        if turn.get("summary"):
            conv_text += f"System (Zusammenfassung): {turn['summary'].get('message', '')}\n"
        conv_text += "\n"

    last_angebot = angebote[-1] if angebote else {}
    angebot_text = json.dumps(last_angebot, indent=2, ensure_ascii=False)[:3000] if last_angebot else "Kein Angebot erstellt"
    prov_text = json.dumps(provenance, indent=2, ensure_ascii=False)[:3000] if provenance else "Keine Provenance-Daten"

    scenario_desc = (
        f"ID: {scenario.id} — {scenario.name}\n"
        f"Persona: {scenario.persona}\n"
        f"Gebäude: {scenario.gebaeude}\n"
        f"Kategorie: {scenario.category}"
    )

    prompt = (JUDGE_SYSTEM
        .replace("{scenario_description}", scenario_desc)
        .replace("{expected}", json.dumps(scenario.expected, ensure_ascii=False))
        .replace("{tricky_aspect}", scenario.tricky_aspect)
        .replace("{conversation}", conv_text)
        .replace("{angebot}", angebot_text)
        .replace("{provenance}", prov_text)
    )

    llm = ClaudeLLM(model=SONNET_MODEL)
    result = None
    last_error = ""
    for attempt in range(3):
        try:
            response = await llm.chat(
                messages=[
                    {"role": "system", "content": prompt},
                    {"role": "user", "content": "Bewerte diese Konversation anhand der Preisregeln. Antworte NUR mit JSON."},
                ],
                max_tokens=4096,
                temperature=0.0,
            )
            result = _parse_json(response.text)
            if result and "scores" in result:
                break
            last_error = f"Attempt {attempt+1}: no 'scores' in parsed result ({len(response.text)} chars, stop={response.stop_reason})"
        except Exception as e:
            last_error = f"Attempt {attempt+1}: {e}"
            await asyncio.sleep(1)

    if not result or "scores" not in result:
        verdict.error = last_error
        for dim in JUDGE_DIMENSIONS:
            verdict.scores[dim] = 0
        verdict.avg_score = 0.0
        return verdict

    try:
        scores = result.get("scores", {})
        reasoning = result.get("reasoning", {})

        for dim in JUDGE_DIMENSIONS:
            score = scores.get(dim)
            if isinstance(score, (int, float)) and 0 <= score <= 5:
                verdict.scores[dim] = int(score)
            else:
                verdict.scores[dim] = 0
                verdict.reasoning[dim] = f"Missing or invalid score: {score}"
            if dim in reasoning and isinstance(reasoning[dim], str):
                verdict.reasoning[dim] = reasoning[dim]

    except Exception as e:
        verdict.error = str(e)
        for dim in JUDGE_DIMENSIONS:
            verdict.scores[dim] = 0

    if verdict.scores:
        verdict.avg_score = sum(verdict.scores.values()) / len(verdict.scores)
    verdict.passed = verdict.avg_score >= 3.0 and not verdict.error
    return verdict
