"""DGUV V3 ortsfeste elektrische Anlage Merkmale.

PRD v2.1 — erweitert um Reifegrad, Dokumentationsumfang, Referenzpreis, Nutzungs-Mix.
"""

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, field_validator


class GebaeudeNutzungDGUV(str, Enum):
    BUEROGEBAEUDE = "buerogebaeude"
    SERVICE_CENTER = "service_center"
    SENIORENTREFF = "seniorentreff"
    HOTEL = "hotel"
    KRANKENHAUS = "krankenhaus"
    INDUSTRIE = "industrie"
    SCHULE = "schule"
    VERKAUFSSTAETTE = "verkaufsstaette"
    TIEFGARAGE = "tiefgarage"
    VERSAMMLUNGSSTAETTE = "versammlungsstaette"
    MOEBELHAUS = "moebelhaus"
    GARTENMARKT = "gartenmarkt"
    SONSTIGE = "sonstige"


class Netzform(str, Enum):
    TN_C_S = "tn_c_s"
    TN_S = "tn_s"
    TT = "tt"
    IT = "it"


class Installationskategorie(int, Enum):
    """Kalkulationshilfen NBG + S. Veit Mail 30.05."""
    KAT_1 = 1  # Wohnung, Freiflächen, Allgemeinbereiche
    KAT_2 = 2  # Büro, Schule, Restaurant, Lager, Krankenhaus AG0, Altenheim
    KAT_3 = 3  # Supermarkt, Produktion (einfach), Museum, EDV, Versammlungsräume
    KAT_4 = 4  # Technikräume, Reinraum
    KAT_5 = 5  # Sonder (OP, Labor)
    KAT_6 = 6  # NSHV, Trafo, Batterieladestation (S. Veit Mail 30.05)


class Reifegrad(int, Enum):
    """S. Veit Mail 30.05 Punkt 7."""
    RG_1 = 1  # Ungeordneter Anlagenbetrieb
    RG_2 = 2  # Reaktiver Anlagenbetrieb
    RG_3 = 3  # Strukturierter Regelbetrieb (Standard = 100%)
    RG_4 = 4  # Hochprofessioneller Betrieb


class NutzungsMixEintrag(BaseModel):
    """Ein Anteil im Nutzungs-Mix, z.B. 30% Büro."""
    nutzung: str = Field(description="z.B. 'Büro', 'Logistik', 'Produktion', 'Technik'")
    anteil: float = Field(ge=0, le=1.0, description="Anteil als Dezimal, z.B. 0.30 für 30%")
    kategorie: Optional[Installationskategorie] = None


class DGUVMerkmale(BaseModel):
    """Input für Kalkulator DGUV V3 ortsfeste elektrische Anlage."""

    nutzung: GebaeudeNutzungDGUV
    adresse_strasse: Optional[str] = None
    adresse_plz: Optional[str] = None
    adresse_ort: Optional[str] = None
    adresse_lat: Optional[float] = None
    adresse_lon: Optional[float] = None

    gesamtflaeche_m2: float = Field(
        ge=1, le=1_000_000,
        description="Gesamte Fläche in m² (primary cost driver)",
    )
    errichtungszeitraum: Optional[str] = None
    baujahr: Optional[int] = None

    netzform: Optional[Netzform] = None
    netzbetreiber: Optional[str] = None
    einspeisung_ms_trafo: bool = False
    leistung_trafo_kva: Optional[float] = None
    ueberspannungsschutz_vorhanden: bool = False

    primary_installationskategorie: Installationskategorie = Installationskategorie.KAT_2

    nutzungs_mix: Optional[list[NutzungsMixEintrag]] = None

    anzahl_verteilungen_uv: int = Field(0, ge=0, description="Unterverteilungen")
    anzahl_verteilungen_hv: int = Field(0, ge=0, description="Hauptverteilungen")
    anzahl_verteilungen_nshv: int = Field(0, ge=0, description="Niederspannungshauptverteilungen")

    nea_vorhanden: bool = False
    sv_nshv_vorhanden: bool = False

    reifegrad: Reifegrad = Reifegrad.RG_3
    vollerfassung: bool = False

    referenzpreis_jahr: Optional[int] = Field(None, ge=2015, le=2026)
    referenzpreis_betrag: Optional[float] = Field(None, ge=0)

    baurechtlich: bool = False
    vereinsmitglied: bool = True
    eilzuschlag: bool = False
    erstpruefung: bool = False

    vds_pruefung: bool = False
    pv_kwp: Optional[float] = Field(None, ge=0, description="PV-Anlage kWp")
    pv_norm: str = "din"
    ladesaeulen: Optional[list] = None

    @field_validator("nutzungs_mix")
    @classmethod
    def _normalize_mix(cls, v):
        if v is None:
            return v
        total = sum(e.anteil for e in v)
        if total > 0 and abs(total - 1.0) > 0.01:
            for e in v:
                e.anteil = e.anteil / total
        return v
