"""DGUV V3 ortsfeste elektrische Anlage Merkmale.

PRD v2.1 — erweitert um Reifegrad, Dokumentationsumfang, Referenzpreis, Nutzungs-Mix.
"""

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, field_validator, model_validator


class Pruefart(str, Enum):
    """AE-1 (Plan v2): EIN Elektro-Produkt mit Diskriminator statt neuer Gewerke.

    Deckt Veit P1 ab ("Prüfart identifizieren"). Löst VdS-Only-Routing
    (Fix 3) und MA560 per-Device (Fix 5) mit einem Konzept.
    """

    DGUV_ORTSFEST = "dguv_ortsfest"            # MA507/501 — ortsfeste Anlagen
    DGUV_ORTSVERAENDERLICH = "dguv_ortsv"      # MA560 — ortsveränderliche Betriebsmittel
    VDS = "vds"                                 # MA505 — nur VdS 2871
    DGUV_PLUS_VDS = "dguv_plus_vds"            # Kombi (Pausch: VdS + 50%)


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
    KAT_7 = 7  # Krankenhaus AG2 (OP, Intensiv) — SRB Kalkulation


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
    """Input für Kalkulator Elektro-Prüfungen (DGUV V3 / VdS / MA560).

    AE-2 (Plan v2): gesamtflaeche_m2 ist Optional — Pflicht-Inputs hängen
    von der Pruefart ab (siehe model_validator unten).
    """

    nutzung: GebaeudeNutzungDGUV
    pruefart: Pruefart = Pruefart.DGUV_ORTSFEST
    adresse_strasse: Optional[str] = None
    adresse_plz: Optional[str] = None
    adresse_ort: Optional[str] = None
    adresse_lat: Optional[float] = None
    adresse_lon: Optional[float] = None

    gesamtflaeche_m2: Optional[float] = Field(
        None, ge=1, le=1_000_000,
        description="Gesamte Fläche in m² (primary cost driver bei ortsfest/VdS)",
    )
    anzahl_betriebsmittel: Optional[int] = Field(
        None, ge=1,
        description="Anzahl ortsveränderlicher Betriebsmittel (MA560, per-Device)",
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

    referenzpreis_jahr: Optional[int] = Field(None, ge=2010, le=2026)
    referenzpreis_betrag: Optional[float] = Field(None, ge=0)
    referenz_vergleichbar: bool = False

    baurechtlich: bool = False
    vereinsmitglied: bool = True
    eilzuschlag: bool = False
    erstpruefung: bool = False

    # DEPRECATED Alias (Plan v2 AE-2): vds_pruefung=True wird vom Validator
    # auf pruefart=DGUV_PLUS_VDS gemappt. Neue Aufrufer setzen pruefart direkt.
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

    @model_validator(mode="after")
    def _pruefart_pflicht_inputs(self):
        """AE-2: Pflicht-Inputs je Pruefart + vds_pruefung-Alias-Mapping."""
        # Deprecated Alias: vds_pruefung=True → Kombi-Prüfung
        if self.vds_pruefung and self.pruefart == Pruefart.DGUV_ORTSFEST:
            self.pruefart = Pruefart.DGUV_PLUS_VDS
        # Alias synchron halten — Engine-Pfade prüfen noch vds_pruefung
        if self.pruefart == Pruefart.DGUV_PLUS_VDS:
            self.vds_pruefung = True

        if self.pruefart == Pruefart.DGUV_ORTSVERAENDERLICH:
            if self.anzahl_betriebsmittel is None:
                raise ValueError(
                    "Pruefart 'dguv_ortsv' (MA560) benötigt anzahl_betriebsmittel"
                )
        else:
            verteilungen = (
                self.anzahl_verteilungen_uv
                + self.anzahl_verteilungen_hv
                + self.anzahl_verteilungen_nshv
            )
            if self.gesamtflaeche_m2 is None and verteilungen == 0:
                raise ValueError(
                    f"Pruefart '{self.pruefart.value}' benötigt gesamtflaeche_m2 "
                    "ODER Verteilungen (UV/HV/NSHV) als Mengen-Input"
                )
        return self
