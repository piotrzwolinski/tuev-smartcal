"""DGUV V3 ortsfeste elektrische Anlage Merkmale.

~12 core Merkmale z MA507 sample PDFs. Phase 1 core model.
TODO M3.4: rozszerzyć o per-Stromkreis tabele (Gersthofen-level granularity).
"""

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class GebaeudeNutzungDGUV(str, Enum):
    BUEROGEBAEUDE = "buerogebaeude"
    SERVICE_CENTER = "service_center"
    SENIORENTREFF = "seniorentreff"
    HOTEL = "hotel"
    KRANKENHAUS = "krankenhaus"
    INDUSTRIE = "industrie"
    SCHULE = "schule"
    VERKAUFSSTAETTE = "verkaufsstaette"
    SONSTIGE = "sonstige"


class Netzform(str, Enum):
    TN_C_S = "tn_c_s"    # najczęstsza w DE
    TN_S = "tn_s"
    TT = "tt"
    IT = "it"


class Installationskategorie(int, Enum):
    """LPV B04 Kap. 2: 5 Flächenfaktoren per Raum-Nutzung."""
    KAT_1 = 1  # Bürofläche (niedrigszy)
    KAT_2 = 2  # Produktion
    KAT_3 = 3  # Lager
    KAT_4 = 4  # Verkehrsfläche
    KAT_5 = 5  # Sonder (höchszy)


class DGUVMerkmale(BaseModel):
    """Input dla Kalkulatora DGUV V3 ortsfeste elektrische Anlage."""

    nutzung: GebaeudeNutzungDGUV
    adresse_strasse: Optional[str] = None
    adresse_plz: Optional[str] = None
    adresse_ort: Optional[str] = None
    adresse_lat: Optional[float] = None
    adresse_lon: Optional[float] = None

    # Gebäudedaten
    gesamtflaeche_m2: float = Field(
        ge=1, le=1_000_000,
        description="Gesamte Fläche Anlage w m² (primary cost driver)",
    )
    errichtungszeitraum: Optional[str] = None
    baujahr: Optional[int] = None

    # Netzdaten
    netzform: Optional[Netzform] = None
    netzbetreiber: Optional[str] = None
    einspeisung_ms_trafo: bool = False      # MS-Hausanschluss z trafo
    leistung_trafo_kva: Optional[float] = None
    ueberspannungsschutz_vorhanden: bool = False

    # Fläche per Installationskategorie (cost driver)
    # TODO M3.4: detailed breakdown — na razie single-cat approximation
    primary_installationskategorie: Installationskategorie = Installationskategorie.KAT_1

    # Anzahl Verteilungen (Grundkosten)
    anzahl_verteilungen_uv: int = Field(0, ge=0, description="Unterverteilungen")
    anzahl_verteilungen_hv: int = Field(0, ge=0, description="Hauptverteilungen")
    anzahl_verteilungen_nshv: int = Field(0, ge=0, description="Niederspannungshauptverteilungen")

    # Räume besonderer Nutzung (Zuschläge)
    nea_vorhanden: bool = False
    sv_nshv_vorhanden: bool = False

    # Prüfung context
    baurechtlich: bool = False      # DGUV V3 = kundenauftrag, non-baurecht — usually false
    vereinsmitglied: bool = True
    eilzuschlag: bool = False
    erstpruefung: bool = False
