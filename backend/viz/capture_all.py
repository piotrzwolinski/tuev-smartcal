"""Batch-Capture aller 16 Testrunde-1 Fälle via GraphPricingEngine (= Produktion).
Modul NEBEN der Engine — nur calculate() + provenance lesen. Dump → viz/out/cases_all.json.
Merkmale 1:1 aus scripts/test_testrunde1_all.py.
"""
import json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from engine.graph_pricing_engine import GraphPricingEngine
from engine.gewerk import get_gewerk
from products.dguv_v3.merkmale import (
    DGUVMerkmale, GebaeudeNutzungDGUV, Installationskategorie, Pruefart, NutzungsMixEintrag,
)
import products.dguv_v3, products.blitzschutz  # noqa

K = Installationskategorie
N = GebaeudeNutzungDGUV
P = Pruefart
OUT = Path(__file__).resolve().parent / "out"
OUT.mkdir(exist_ok=True)

CASES = [
  ("T01","Hipp Pfaffenhofen (VdS)",6850,11877,dict(nutzung=N.INDUSTRIE,pruefart=P.VDS,gesamtflaeche_m2=20000,anzahl_verteilungen_uv=45,primary_installationskategorie=K.KAT_3,adresse_lat=48.53,adresse_lon=11.49,adresse_plz="85276")),
  ("T02","REWE Eching (RV)",657.26,2125.28,dict(nutzung=N.VERKAUFSSTAETTE,gesamtflaeche_m2=800,adresse_lat=48.30,adresse_lon=11.62,adresse_plz="85386")),
  ("T03","badenova Schaltschrank",391,1051.06,dict(nutzung=N.SONSTIGE,anzahl_verteilungen_nshv=1,adresse_lat=48.16,adresse_lon=7.85,adresse_plz="77933")),
  ("T04","Auto Service Calw (MA560)",1216.95,1198.33,dict(nutzung=N.INDUSTRIE,pruefart=P.DGUV_ORTSVERAENDERLICH,anzahl_betriebsmittel=114,adresse_lat=48.71,adresse_lon=8.73,adresse_plz="75365")),
  ("T05","Landwirt Neukirchen (MA560)",174.80,1400,dict(nutzung=N.INDUSTRIE,pruefart=P.DGUV_ORTSVERAENDERLICH,anzahl_betriebsmittel=23,adresse_lat=49.32,adresse_lon=12.38,adresse_plz="93444")),
  ("T06","Maritim Hotel (MA510)",220,4063.50,dict(nutzung=N.HOTEL,gesamtflaeche_m2=3000,anzahl_verteilungen_uv=40,adresse_lat=52.02,adresse_lon=8.53,adresse_plz="32105")),
  ("T07","König & Bauer (VdS)",None,None,dict(nutzung=N.INDUSTRIE,pruefart=P.VDS,gesamtflaeche_m2=900,anzahl_verteilungen_uv=48,nutzungs_mix=[NutzungsMixEintrag(nutzung="Produktion",anteil=0.80,kategorie=K.KAT_3),NutzungsMixEintrag(nutzung="Verwaltung",anteil=0.20,kategorie=K.KAT_2)],adresse_lat=51.11,adresse_lon=13.65,adresse_plz="01445")),
  ("T08","Apleona Gilching (DGUV+VdS)",7932,10370,dict(nutzung=N.BUEROGEBAEUDE,pruefart=P.DGUV_PLUS_VDS,gesamtflaeche_m2=26000,anzahl_verteilungen_uv=37,adresse_lat=48.11,adresse_lon=11.30,adresse_plz="82205")),
  ("T09","Weber-Gymnasium (MULTI)",4800,2834,dict(nutzung=N.SCHULE,gesamtflaeche_m2=5000,adresse_lat=48.15,adresse_lon=11.57,adresse_plz="80331")),
  ("T10","Max Planck RZ (MA560)",5341,2084,dict(nutzung=N.INDUSTRIE,pruefart=P.DGUV_ORTSVERAENDERLICH,anzahl_betriebsmittel=545,adresse_lat=48.26,adresse_lon=11.67,adresse_plz="85540")),
  ("T11","REWE München (RV)",657.26,1738.54,dict(nutzung=N.VERKAUFSSTAETTE,gesamtflaeche_m2=1600,adresse_lat=48.14,adresse_lon=11.51,adresse_plz="85540")),
  ("T12","Helios Klinik (DGUV+VdS)",13110,10840,dict(nutzung=N.KRANKENHAUS,pruefart=P.DGUV_PLUS_VDS,gesamtflaeche_m2=18000,nutzungs_mix=[NutzungsMixEintrag(nutzung="Allgemein",anteil=0.70,kategorie=K.KAT_2),NutzungsMixEintrag(nutzung="Technik/OP",anteil=0.30,kategorie=K.KAT_7)],adresse_lat=48.14,adresse_lon=11.45,adresse_plz="81249")),
  ("T13","Motel One München (RV)",621,5161.31,dict(nutzung=N.HOTEL,gesamtflaeche_m2=6000,adresse_lat=48.14,adresse_lon=11.57,adresse_plz="80331")),
  ("T14","roMEd Klinik Prien",3470,4322.74,dict(nutzung=N.KRANKENHAUS,gesamtflaeche_m2=8000,nutzungs_mix=[NutzungsMixEintrag(nutzung="Allgemein",anteil=0.70,kategorie=K.KAT_2),NutzungsMixEintrag(nutzung="Technik",anteil=0.30,kategorie=K.KAT_7)],adresse_lat=47.85,adresse_lon=12.34,adresse_plz="83209")),
  ("T15","DGUV Würzburg",4195.25,3282.37,dict(nutzung=N.BUEROGEBAEUDE,gesamtflaeche_m2=5000,adresse_lat=49.80,adresse_lon=9.95,adresse_plz="97080")),
]


def _ser(v):
    if hasattr(v, "value"):
        return v.value
    if isinstance(v, list):
        return [f"{getattr(e,'nutzung','?')} {getattr(e,'anteil','')*100:.0f}% {getattr(getattr(e,'kategorie',None),'value','')}" if hasattr(e, "nutzung") else str(e) for e in v]
    return v


def cap(cid, label, real, v1, mk):
    g = get_gewerk("dguv_v3")
    e = GraphPricingEngine(g.graph_name)
    m = DGUVMerkmale(**mk)
    a = e.calculate(g, m)
    delta = (a.total - real) / real * 100 if real else None
    return {"id": cid, "label": label, "real": real, "v1": v1,
            "total": round(a.total, 2),
            "breakdown": a.breakdown.to_dict(), "confidence": round(a.confidence, 3),
            "delta": round(delta, 1) if delta is not None else None,
            "inputs": {k: _ser(v) for k, v in mk.items() if k not in ("adresse_lat", "adresse_lon")},
            "provenance": e.provenance}


def cap_t16():
    from products.blitzschutz.merkmale import BlitzschutzMerkmale, GebaeudeNutzung
    g = get_gewerk("blitzschutz")
    e = GraphPricingEngine(g.graph_name)
    m = BlitzschutzMerkmale(nutzung=GebaeudeNutzung.SONSTIGE, anzahl_ableitungen=12,
                            adresse_lat=48.26, adresse_lon=11.44, adresse_plz="85221")
    a = e.calculate(g, m)
    return {"id": "T16", "label": "Polizei Dachau (Blitz)", "real": 205, "v1": 1536.66,
            "total": round(a.total, 2), "breakdown": a.breakdown.to_dict(),
            "confidence": round(a.confidence, 3), "delta": round((a.total - 205) / 205 * 100, 1),
            "inputs": {"nutzung": "sonstige", "anzahl_ableitungen": 12, "produkt": "Blitzschutz MA574"},
            "provenance": e.provenance}


if __name__ == "__main__":
    out = []
    for cid, label, real, v1, mk in CASES:
        try:
            d = cap(cid, label, real, v1, mk)
            out.append(d)
            rs = f"{real:,.0f}" if real else "—"
            ds = f"{d['delta']:+.0f}%" if d['delta'] is not None else "—"
            print(f"{cid}: {d['total']:>8,.0f}€  real {rs:>7}  {ds:>6}  ({len(d['provenance'])} steps)")
        except Exception as ex:
            print(f"{cid}: FEHLER {type(ex).__name__}: {ex}")
    try:
        d = cap_t16(); out.append(d)
        print(f"T16: {d['total']:>8,.0f}€  real {d['real']:>7}  {d['delta']:+.0f}%  ({len(d['provenance'])} steps)")
    except Exception as ex:
        print(f"T16: FEHLER {ex}")
    (OUT / "cases_all.json").write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n→ {OUT/'cases_all.json'} ({len(out)} Fälle)")
