"""PII Anonymizer for TÜV Prüfberichte — pre-LLM processing.

Removes/pseudonymizes all personally identifiable + confidential business data
BEFORE sending to external LLM (Claude Haiku).

Strategy:
- Regex-based replacement with deterministic pseudo-IDs (hash-based)
- Mapping table stored locally → allows post-processing to restore real IDs
- LLM receives only anonymized content

Scope (DACH-specific):
- Adresse: Straße + Hausnr + PLZ + Ort
- Personen: Sachverständiger, Ansprechpartner (by context: "Der Sachverständige NAME")
- Firmen/Organisationen: Auftraggeber, Betreiber, Standort-Name
- Numery: Auftrags-Nr, Equipment-Nr, Material-Nr, Fabriknummer, Prüfbuchnummer
- Kontakty: Telefon, Telefax, E-Mail
- Secrets: Passwörter, Access-Codes (Netinform etc.)
- TÜV-Infrastruktur: explizite Abteilung/Niederlassung-Namen — bleiben (kein PII)
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field


def _pseudo(value: str, prefix: str) -> str:
    """Deterministic 6-char hash-pseudonym."""
    h = hashlib.sha256(value.encode("utf-8")).hexdigest()[:6].upper()
    return f"<{prefix}_{h}>"


@dataclass
class AnonymizationResult:
    anonymized_text: str
    mapping: dict[str, str] = field(default_factory=dict)  # pseudo_id -> original
    categories: dict[str, int] = field(default_factory=dict)  # stats

    def inverse_map(self) -> dict[str, str]:
        """Return original -> pseudo_id."""
        return {v: k for k, v in self.mapping.items()}


# ───────────────────────────────────────────────────
# Regex patterns
# ───────────────────────────────────────────────────

# TÜV-owned (kein PII — bleiben):
TUEV_WHITELIST = {
    "TÜV SÜD Industrie Service GmbH",
    "TÜV SÜD", "TÜV-Daten", "Netinform",
}

# Phone numbers: DE format (0xxx xxxx-xxxx / +49 / 030 / 089)
_PHONE_RE = re.compile(r"\b(?:\+49|0)\s?(?:\d{2,5})[\s/-]?\d{3,10}(?:-\d{2,5})?\b")

# Email
_EMAIL_RE = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")

# Auftrags/Equipment/Material numbers
_AUFTRAG_RE = re.compile(r"(Auftrags-Nr\.?|Auftragsnummer)\s*:\s*(\d{5,12})", re.IGNORECASE)
_EQUIPMENT_RE = re.compile(r"(Equipment-Nr\.?|Equipment)\s*:\s*(\d{5,12})", re.IGNORECASE)
_MATERIAL_RE = re.compile(r"(Material(?:-Nr\.?)?)\s*:\s*([A-Z0-9-]+)", re.IGNORECASE)
_FABRIK_RE = re.compile(r"(Fabriknummer|Fabrik-Nr\.?)\s*:\s*([A-Z0-9-]+)", re.IGNORECASE)
_PRUEFBUCH_RE = re.compile(r"(Prüfbuchnummer|Prüfbuch-Nr\.?)\s*:\s*([A-Z0-9-]+)", re.IGNORECASE)

# Netinform password (specific pattern from TÜV reports)
_PASSWORD_RE = re.compile(r"(Passwort\s*(?:Netinform)?)\s*:?\s*([A-Za-z0-9]{5,20})", re.IGNORECASE)

# Addresses (heurystyka DE):
# Straßenname: X-straße, X-str., X-weg, X-allee, X-platz etc. + Hausnr.
_STREET_RE = re.compile(
    r"\b([A-ZÄÖÜ][A-Za-zäöüß.-]+(?:str(?:aße|\.)?|weg|allee|platz|ring|gasse|ufer|damm))\s+(\d+\s*[a-zA-Z]?)\b",
)
# PLZ + Ort (5 digit + city)
_PLZ_ORT_RE = re.compile(r"\b(\d{5})\s+([A-ZÄÖÜ][a-zäöüß-]+(?:\s[A-ZÄÖÜ][a-zäöüß-]+)?)\b")

# Person names — context "Der Sachverständige FIRSTNAME LASTNAME"
_PERSON_CONTEXT_RE = re.compile(
    r"(Der Sachverständige|Die Sachverständige|Sachverständiger?|Prüfer|Herr|Frau|Dr\.|Dipl\.-Ing\.)\s+([A-ZÄÖÜ][a-zäöüß]+(?:\s+[A-ZÄÖÜ][a-zäöüß]+){0,2})"
)

# Firmennamen "Gemeinde X" / "Stadt X" / "Stadtwerke X" etc.
_ORG_RE = re.compile(
    r"\b(Gemeinde|Stadt|Stadtwerke|Landkreis|Bezirk|Schön\s+Klinik|Kreisverwaltung|Marktgemeinde)\s+([A-ZÄÖÜ][a-zäöüß.-]+(?:\s+[A-ZÄÖÜ][a-zäöüß.-]+)?)"
)

# Building names ending in "-schule/klinik/stadion/heim" etc.
# Captures: group 1 = full name, group 2 = type (schule/klinik/...)
_BUILDING_RE = re.compile(
    r"\b([A-ZÄÖÜ][A-Za-zäöüß-]{3,30}-?(schule|gymnasium|kindergarten|kita|klinik|krankenhaus|stadion|heim|kirche|halle|werk|zentrum|depot|bibliothek|museum|turnhalle))\b",
    re.IGNORECASE,
)

# Type-preserving mapping (Gebäudekategorie zostaje widoczna dla LLM)
_BUILDING_TYPE_MAP = {
    "schule": "SCHULE", "gymnasium": "SCHULE", "kindergarten": "SCHULE",
    "kita": "SCHULE", "turnhalle": "SCHULE",
    "klinik": "KRANKENHAUS", "krankenhaus": "KRANKENHAUS",
    "heim": "HEIM", "kirche": "KIRCHE", "stadion": "STADION",
    "halle": "HALLE", "werk": "INDUSTRIE", "zentrum": "ZENTRUM",
    "depot": "DEPOT", "bibliothek": "BIBLIOTHEK", "museum": "MUSEUM",
}


def anonymize_pdf_text(text: str) -> AnonymizationResult:
    """Anonymize raw PDF text from TÜV Prüfbericht.

    Returns:
        AnonymizationResult z anonymized_text (gotowe do LLM) i mapping
        dla post-processingu.
    """
    mapping: dict[str, str] = {}
    categories: dict[str, int] = {}

    def _replace(pattern, cat: str, prefix: str, anonymized: str, key_fn=None) -> str:
        def sub(m):
            if key_fn:
                original, to_replace = key_fn(m)
            else:
                original = m.group(0)
                to_replace = original
            pseudo = _pseudo(original, prefix)
            mapping[pseudo] = original
            categories[cat] = categories.get(cat, 0) + 1
            return anonymized.replace(to_replace, pseudo)
        return pattern.sub(sub, anonymized)

    out = text

    # 1. Numeryczne identyfikatory (label preserved, value replaced)
    def _label_num(m):
        label, val = m.group(1), m.group(2)
        return (val, m.group(0).replace(val, val))  # key = raw val

    for pat, cat, prefix in [
        (_AUFTRAG_RE, "auftrags_nr", "AUF"),
        (_EQUIPMENT_RE, "equipment_nr", "EQ"),
        (_MATERIAL_RE, "material_nr", "MAT"),
        (_FABRIK_RE, "fabrik_nr", "FAB"),
        (_PRUEFBUCH_RE, "pruefbuch_nr", "PBN"),
    ]:
        def sub(m, prefix=prefix, cat=cat):
            label, val = m.group(1), m.group(2)
            pseudo = _pseudo(val, prefix)
            mapping[pseudo] = val
            categories[cat] = categories.get(cat, 0) + 1
            return f"{label}: {pseudo}"
        out = pat.sub(sub, out)

    # 2. Passwords — CRITICAL (e.g. Netinform)
    def sub_pw(m):
        label, val = m.group(1), m.group(2)
        pseudo = _pseudo(val, "PW")
        mapping[pseudo] = val
        categories["password"] = categories.get("password", 0) + 1
        return f"{label}: {pseudo}"
    out = _PASSWORD_RE.sub(sub_pw, out)

    # 3. E-Mails (replace tylko user-specific, zostaw @tuvsud.com generic)
    def sub_email(m):
        original = m.group(0)
        pseudo = _pseudo(original, "EMAIL")
        mapping[pseudo] = original
        categories["email"] = categories.get("email", 0) + 1
        return pseudo
    out = _EMAIL_RE.sub(sub_email, out)

    # 4. Phone numbers
    def sub_phone(m):
        original = m.group(0)
        pseudo = _pseudo(original, "TEL")
        mapping[pseudo] = original
        categories["phone"] = categories.get("phone", 0) + 1
        return pseudo
    out = _PHONE_RE.sub(sub_phone, out)

    # 5. Addresses — Straße + Hausnr
    def sub_street(m):
        original = m.group(0)
        pseudo = _pseudo(original, "ADR")
        mapping[pseudo] = original
        categories["street"] = categories.get("street", 0) + 1
        return pseudo
    out = _STREET_RE.sub(sub_street, out)

    # 6. PLZ + Ort (after street replacement to avoid collision)
    def sub_plz(m):
        original = m.group(0)
        plz, ort = m.group(1), m.group(2)
        # PLZ itself is not very identifying, but combined with Ort yes
        pseudo = _pseudo(original, "CITY")
        mapping[pseudo] = original
        categories["plz_ort"] = categories.get("plz_ort", 0) + 1
        return pseudo
    out = _PLZ_ORT_RE.sub(sub_plz, out)

    # 7. Persons (context-based)
    def sub_person(m):
        label, name = m.group(1), m.group(2)
        if name in TUEV_WHITELIST:
            return m.group(0)
        pseudo = _pseudo(name, "SV")
        mapping[pseudo] = name
        categories["person"] = categories.get("person", 0) + 1
        return f"{label} {pseudo}"
    out = _PERSON_CONTEXT_RE.sub(sub_person, out)

    # 8. Organization names (Gemeinde/Stadt X)
    def sub_org(m):
        label, name = m.group(1), m.group(2)
        original = m.group(0)
        pseudo = _pseudo(original, "ORG")
        mapping[pseudo] = original
        categories["organization"] = categories.get("organization", 0) + 1
        return pseudo
    out = _ORG_RE.sub(sub_org, out)

    # 9. Building names — TYPE-PRESERVING (LLM still sees category)
    def sub_building(m):
        original = m.group(0)
        type_suffix = m.group(2).lower()
        type_code = _BUILDING_TYPE_MAP.get(type_suffix, "BLDG")
        pseudo = _pseudo(original, type_code)
        mapping[pseudo] = original
        categories["building"] = categories.get("building", 0) + 1
        return pseudo
    out = _BUILDING_RE.sub(sub_building, out)

    # 10. Second-pass: extract unique city names from mapping (from PLZ+Ort matches)
    # and mask all other occurrences of that city name.
    # Rationale: "94118 Jandelsbrunn" caught in pass 1, but standalone "Jandelsbrunn"
    # elsewhere (e.g. "Mittelschule Jandelsbrunn") was not masked.
    cities_in_mapping = set()
    for pseudo, orig in list(mapping.items()):
        if pseudo.startswith("<CITY_"):
            # Extract city name (po PLZ 5-digit)
            m = re.match(r"^\s*\d{5}\s+(.+)$", orig)
            if m:
                cities_in_mapping.add(m.group(1).strip())

    for city_name in sorted(cities_in_mapping, key=len, reverse=True):  # longest first
        # Replace standalone occurrences of city name (not already in pseudo)
        pseudo = _pseudo(city_name, "CITY2")
        pattern = rf"\b{re.escape(city_name)}\b"
        count_before = len(re.findall(pattern, out))
        out = re.sub(pattern, pseudo, out)
        if count_before > 0 and pseudo not in mapping:
            mapping[pseudo] = city_name
            categories["city_2pass"] = categories.get("city_2pass", 0) + count_before

    return AnonymizationResult(
        anonymized_text=out,
        mapping=mapping,
        categories=categories,
    )
