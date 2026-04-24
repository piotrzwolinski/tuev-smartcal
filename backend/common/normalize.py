"""Post-processing normalization of LLM-extracted Merkmale → Pydantic enum values.

Problem: Haiku zwraca valid semantyczne wartości które są slightly off naszych enum values:
- "kindergarten" → should map to "schule"
- "aluminium" → "alulegierung"
- "verzinkter Stahl" → "stahl_verzinkt"
- "aluminium, verzinkter stahl" → pick first or "gemischt"
- "3" → "III"
- "unbekannt" → null

Ten moduł wykonuje deterministic mapping PRZED Pydantic validation.
"""

import re
from typing import Any, Optional


# ──────────────────────────────────────────────────────────────
# Blitzschutz-specific normalizers
# ──────────────────────────────────────────────────────────────

NUTZUNG_MAP = {
    "schule": "schule", "gymnasium": "schule", "kindergarten": "schule",
    "kita": "schule", "hort": "schule", "grundschule": "schule",
    "mittelschule": "schule", "realschule": "schule", "berufsschule": "schule",
    "turnhalle": "schule", "sporthalle": "schule", "universitaet": "schule",
    "buero": "buero", "verwaltung": "buero", "rathaus": "buero",
    "industrie": "industrie", "werkstatt": "industrie", "fabrik": "industrie",
    "wohnung": "wohnung", "wohnhaus": "wohnung", "mehrfamilienhaus": "wohnung",
    "einfamilienhaus": "wohnung", "wohngebaeude": "wohnung",
    "hotel": "hotel", "pension": "hotel", "gasthaus": "hotel",
    "museum": "museum", "burg": "museum", "schloss": "museum",
    "kirche": "museum", "dom": "museum", "kapelle": "museum",
    "krankenhaus": "krankenhaus", "klinik": "krankenhaus", "altenheim": "krankenhaus",
    "pflegeheim": "krankenhaus", "senioren": "krankenhaus", "heim": "krankenhaus",
    "lager": "lager", "halle": "lager", "depot": "lager", "bauhof": "lager",
    "garage": "garage", "parkhaus": "garage", "tiefgarage": "garage",
    "sonstige": "sonstige", "sonstiges": "sonstige", "other": "sonstige",
}

SCHUTZKLASSE_MAP = {
    "i": "I", "1": "I", "klasse i": "I", "klasse 1": "I", "sk i": "I", "sk 1": "I",
    "ii": "II", "2": "II", "klasse ii": "II", "klasse 2": "II", "sk ii": "II", "sk 2": "II",
    "iii": "III", "3": "III", "klasse iii": "III", "klasse 3": "III", "sk iii": "III", "sk 3": "III",
    "iv": "IV", "4": "IV", "klasse iv": "IV", "klasse 4": "IV", "sk iv": "IV", "sk 4": "IV",
}

BAUART_MAP = {
    "ziegel": "ziegel", "backstein": "ziegel", "mauerwerk": "ziegel",
    "stahlbeton": "stahlbeton", "beton": "stahlbeton", "stahlbetonbau": "stahlbeton",
    "holz": "holz", "holzbau": "holz", "fachwerk": "holz",
    "stahl": "stahl", "stahlbau": "stahl", "metallbau": "stahl",
    "naturstein": "naturstein", "sandstein": "naturstein", "granit": "naturstein",
    "gemischt": "gemischt", "misch": "gemischt", "gemischte bauweise": "gemischt",
}

DACH_MAP = {
    "blech": "blech", "metall": "blech", "aluminium": "blech", "zink": "blech",
    "kies": "kies", "kiesdach": "kies",
    "folie": "folie", "bitumen": "folie", "flachdach": "folie", "pvc": "folie",
    "ziegel": "ziegel", "dachziegel": "ziegel", "tondach": "ziegel",
    "dachpappe": "dachpappe", "teerpappe": "dachpappe",
    "gruendach": "gruendach", "extensivdach": "gruendach",
    "gemischt": "gemischt",
}

MATERIAL_MAP = {
    "kupfer": "kupfer", "cu": "kupfer", "copper": "kupfer",
    "alulegierung": "alulegierung", "aluminium": "alulegierung", "alu": "alulegierung",
    "al": "alulegierung", "almg": "alulegierung",
    "stahl_verzinkt": "stahl_verzinkt", "verzinkter stahl": "stahl_verzinkt",
    "stahl verzinkt": "stahl_verzinkt", "feuerverzinkt": "stahl_verzinkt",
    "stahl": "stahl_verzinkt",  # assumption: blank stahl default verzinkt dla Blitzschutz
    "edelstahl": "edelstahl", "nirosta": "edelstahl", "v2a": "edelstahl", "v4a": "edelstahl",
    "inox": "edelstahl", "rostfrei": "edelstahl",
    "metallene_fassade": "metallene_fassade", "fassade": "metallene_fassade",
    "metallfassade": "metallene_fassade", "natuerliche ableitung": "metallene_fassade",
    "gemischt": "gemischt",
}

ERDUNG_MAP = {
    "typ_a": "typ_a", "typ a": "typ_a", "a": "typ_a", "tiefenerder": "typ_a",
    "vertikaler erder": "typ_a",
    "typ_b": "typ_b", "typ b": "typ_b", "b": "typ_b", "fundamenterder": "typ_b",
    "ringerder": "typ_b", "horizontaler erder": "typ_b",
}

ART_PRUEFUNG_MAP = {
    "wiederkehrende": "wiederkehrende", "wp": "wiederkehrende",
    "wiederkehrend": "wiederkehrende", "umfassende": "wiederkehrende",
    "umfassend": "wiederkehrende",
    "nach_instandsetzung": "nach_instandsetzung", "pi": "nach_instandsetzung",
    "instandsetzung": "nach_instandsetzung",
    "nach_montage": "nach_montage", "pm": "nach_montage", "montage": "nach_montage",
    "begutachtung": "begutachtung", "bg": "begutachtung", "gutachten": "begutachtung",
}


def _normalize_via_map(value: Any, mapping: dict, fallback_to_gemischt: bool = False) -> Optional[str]:
    if value is None:
        return None
    s = str(value).strip().lower()

    # Multi-value: "aluminium, verzinkter stahl" → pick first or fall back to "gemischt"
    if "," in s or " und " in s:
        parts = [p.strip() for p in re.split(r"[,/]|\s+und\s+", s)]
        parts = [p for p in parts if p]
        if len(parts) > 1:
            if fallback_to_gemischt:
                return "gemischt"
            # pick first that normalizes cleanly
            for p in parts:
                out = _normalize_via_map(p, mapping, fallback_to_gemischt=False)
                if out:
                    return out

    # Exact match (lowercase)
    if s in mapping:
        return mapping[s]

    # Substring match (keyword-based)
    for key, target in mapping.items():
        if key in s:
            return target

    return None


def normalize_blitzschutz_extracted(extracted: dict) -> dict:
    """Przyjmuje raw dict z LLM, zwraca normalized dict gotowy do Pydantic.

    Fields NOT in extracted lub null → zostają null.
    Fields nieparseowalne → null (lepiej null niż bad data).
    """
    out = dict(extracted)  # shallow copy

    # Nutzung
    out["nutzung"] = _normalize_via_map(out.get("nutzung"), NUTZUNG_MAP) or "sonstige"

    # Schutzklasse (CRITICAL)
    sk = _normalize_via_map(out.get("schutzklasse"), SCHUTZKLASSE_MAP)
    out["schutzklasse"] = sk  # None jeśli nie zidentyfikowano — wtedy Pydantic throw → retry

    # Bauart
    out["bauart"] = _normalize_via_map(out.get("bauart"), BAUART_MAP, fallback_to_gemischt=True)

    # Dacheindeckung
    out["dacheindeckung"] = _normalize_via_map(out.get("dacheindeckung"), DACH_MAP, fallback_to_gemischt=True)

    # Werkstoff / Material
    for field in ("werkstoff_gebaeudeleitung", "material_ableitung", "material_erdungsanlage"):
        out[field] = _normalize_via_map(out.get(field), MATERIAL_MAP, fallback_to_gemischt=True)

    # Erdungsanlage Typ
    out["typ_erdungsanlage"] = _normalize_via_map(out.get("typ_erdungsanlage"), ERDUNG_MAP)

    # Art Prüfung
    out["art_pruefung"] = _normalize_via_map(out.get("art_pruefung"), ART_PRUEFUNG_MAP) or "wiederkehrende"

    # Booleans (cast z "ja"/"nein" / strings)
    for bool_field in ("potentialausgleich_vorhanden", "ueberspannungsschutz_vorhanden",
                        "baurechtlich", "vereinsmitglied", "eilzuschlag", "erstpruefung"):
        v = out.get(bool_field)
        if isinstance(v, str):
            out[bool_field] = v.strip().lower() in ("true", "ja", "yes", "vorhanden", "1")
        elif v is None and bool_field == "vereinsmitglied":
            out[bool_field] = True  # default: większość klientów TÜV to Vereinsmitglieder

    # Clean numeric fields
    for num_field in ("anzahl_ableitungen", "laenge_m", "breite_m", "hoehe_m", "gebaeudeumfang_m"):
        v = out.get(num_field)
        if isinstance(v, str):
            # "35 Stück" → 35
            m = re.search(r"(\d+(?:\.\d+)?)", v)
            if m:
                try:
                    out[num_field] = float(m.group(1)) if "." in m.group(1) else int(m.group(1))
                except ValueError:
                    out[num_field] = None

    return out
