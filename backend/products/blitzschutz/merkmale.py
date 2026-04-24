"""Blitzschutz Merkmale — 17 Merkmale z analizy 30 sample PDFów MA570.

Wszystkie pola mają przykłady z realnych raportów (patrz ~/Desktop/TUEV/dashboard.html → sekcja Blitzschutz).
"""

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, field_validator


# ──────────────────────────────────────────────────────────────
# Enums
# ──────────────────────────────────────────────────────────────

class Schutzklasse(str, Enum):
    I = "I"     # Höchste (Ex-Bereich, Munition)
    II = "II"   # Krankenhaus, Museum, Versammlungsstätten
    III = "III" # Standard (Büro, Industrie, Wohnung) — najczęstsza
    IV = "IV"   # Niedrigste (einfache Wohngebäude, Lager)


class GebaeudeNutzung(str, Enum):
    SCHULE = "schule"
    BUERO = "buero"
    INDUSTRIE = "industrie"
    WOHNUNG = "wohnung"
    HOTEL = "hotel"
    MUSEUM = "museum"
    KRANKENHAUS = "krankenhaus"
    LAGER = "lager"
    GARAGE = "garage"
    SONSTIGE = "sonstige"


class Bauart(str, Enum):
    ZIEGEL = "ziegel"
    STAHLBETON = "stahlbeton"
    HOLZ = "holz"
    STAHL = "stahl"
    NATURSTEIN = "naturstein"
    GEMISCHT = "gemischt"


class Dacheindeckung(str, Enum):
    BLECH = "blech"
    KIES = "kies"
    FOLIE = "folie"
    ZIEGEL = "ziegel"
    DACHPAPPE = "dachpappe"
    GRUENDACH = "gruendach"
    GEMISCHT = "gemischt"


class MaterialAbleitung(str, Enum):
    ALU = "alulegierung"
    KUPFER = "kupfer"
    STAHL_VERZINKT = "stahl_verzinkt"
    EDELSTAHL = "edelstahl"
    METALLENE_FASSADE = "metallene_fassade"
    GEMISCHT = "gemischt"


class TypErdungsanlage(str, Enum):
    TYP_A = "typ_a"  # Vertikaler Tiefenerder
    TYP_B = "typ_b"  # Fundamenterder DIN 18014 / Ringerder


class ArtPruefung(str, Enum):
    WP = "wiederkehrende"
    PI = "nach_instandsetzung"
    PM = "nach_montage"
    BG = "begutachtung"


# ──────────────────────────────────────────────────────────────
# Merkmale schema
# ──────────────────────────────────────────────────────────────

class BlitzschutzMerkmale(BaseModel):
    """Input do Kalkulatora Blitzschutz (17 pól).

    Wszystkie Merkmale są ekstraktowalne z MA570 Prüfberichte (P0 extraction difficulty).
    """

    # Kontext Anfrage (zawsze wymagane)
    nutzung: GebaeudeNutzung = Field(description="Gebäudenutzung")
    adresse_strasse: Optional[str] = None
    adresse_plz: Optional[str] = None
    adresse_ort: Optional[str] = None
    adresse_lat: Optional[float] = None
    adresse_lon: Optional[float] = None

    # Gebäudegeometrie
    laenge_m: Optional[float] = Field(None, ge=0, le=500, description="Länge w m")
    breite_m: Optional[float] = Field(None, ge=0, le=500, description="Breite w m")
    hoehe_m: Optional[float] = Field(None, ge=0, le=300, description="Höhe w m")
    gebaeudeumfang_m: Optional[float] = Field(None, ge=0, le=2000)

    # Bauart
    bauart: Optional[Bauart] = None
    dacheindeckung: Optional[Dacheindeckung] = None
    werkstoff_gebaeudeleitung: Optional[MaterialAbleitung] = None

    # Blitzschutz-core (KEY cost drivers)
    schutzklasse: Optional[Schutzklasse] = Field(
        None,
        description=(
            "DIN EN 62305 Schutzklasse (I/II/III/IV). Optional dla ingest grafu bo "
            "~58% raportów MA570 ma pole niewypełnione (Sachverständiger pominął). "
            "Dla Kalkulatora (user-input) wymagane — walidacja w pipeline."
        ),
    )
    anzahl_ableitungen: int = Field(
        ge=1, le=500,
        description="Anzahl Ableitungen / Messstellen — PRIMARY cost driver (33€/Stück LPV B04 §8.1)",
    )
    material_ableitung: Optional[MaterialAbleitung] = None
    typ_erdungsanlage: Optional[TypErdungsanlage] = None
    material_erdungsanlage: Optional[MaterialAbleitung] = None

    # Shared Blitzschutz features
    potentialausgleich_vorhanden: bool = True
    ueberspannungsschutz_vorhanden: bool = False

    # Prüfung context
    art_pruefung: ArtPruefung = ArtPruefung.WP
    baurechtlich: bool = Field(
        False,
        description="TRUE jeśli Baurecht-driven (MA572) — wymusza Ordnungsprüfung 242€"
    )
    vereinsmitglied: bool = True
    eilzuschlag: bool = False
    erstpruefung: bool = False

    # Validation
    @field_validator("breite_m")
    @classmethod
    def _breite_not_larger_than_laenge(cls, v, info):
        if v is not None and info.data.get("laenge_m") and v > info.data["laenge_m"]:
            return info.data["laenge_m"]  # swap silently
        return v
