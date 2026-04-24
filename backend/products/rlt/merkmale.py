"""RLT Merkmale — 2 sub-warianty (HYG / WPBA).

Phase 1: jeden schema z wariant-discriminator.
TODO M3.3 (KW18): rozszerzyć o pełne VDI 6022 Laborfeldy + BSK per-Stück.
"""

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class RLTVariant(str, Enum):
    HYGIENE = "hygiene"      # MA419-HYG (VDI 6022)
    GARAGE = "garage"        # MA419-WPBA (GaStellV + VDI 2053)


class GaragentTyp(str, Enum):
    MITTEL = "mittelgarage"
    GROSS = "grossgarage"
    KLEIN = "kleingarage"


class FilterklasseISO(str, Enum):
    """ISO 16890 Filterklassen z typowych raportów MA419-HYG."""
    EPM10_50 = "iso_epm10_50"
    EPM2_5_65 = "iso_epm2_5_65"
    EPM1_50 = "iso_epm1_50"
    EPM1_80 = "iso_epm1_80"


class RLTMerkmale(BaseModel):
    """Input dla Kalkulatora RLT."""

    variant: RLTVariant = Field(description="Hygiene VDI 6022 lub Garagenlüftung")
    nutzung_beschreibung: Optional[str] = None

    # Addresse
    adresse_strasse: Optional[str] = None
    adresse_plz: Optional[str] = None
    adresse_ort: Optional[str] = None
    adresse_lat: Optional[float] = None
    adresse_lon: Optional[float] = None

    # Common
    baujahr: Optional[int] = None
    hersteller: Optional[str] = None

    # HYG-specific (MA419-HYG, VDI 6022)
    nennvolumenstrom_m3h: Optional[float] = Field(None, ge=0, description="Nennvolumenstrom m³/h")
    filterklasse_aul: Optional[FilterklasseISO] = None
    filterklasse_zul: Optional[FilterklasseISO] = None
    waermerueckgewinnung: Optional[bool] = None
    umluftbetrieb: Optional[bool] = None
    anzahl_pruefbereiche_hyg: Optional[int] = Field(None, ge=0, description="Liczba bereiche do Laborproben")

    # GARAGE-specific (MA419-WPBA, GaStellV)
    flaeche_m2: Optional[float] = Field(None, ge=0, description="Fläche Garage w m²")
    stellplaetze: Optional[int] = Field(None, ge=0)
    garagentyp: Optional[GaragentTyp] = None
    spez_volumenstrom_m3h_m2: Optional[float] = None
    anzahl_brandschutzklappen: Optional[int] = Field(None, ge=0)
    zeitschaltuhr_vorhanden: Optional[bool] = None
    anzahl_ventilatoren: Optional[int] = Field(None, ge=0, description="Für Grundpreis-Zuschlag 170€/St.")

    # Prüfung context
    baurechtlich: bool = False  # HYG = False, WPBA = True
    vereinsmitglied: bool = True
    eilzuschlag: bool = False
    erstpruefung: bool = False
