"""D-K7 — Kat-7-Rate-Konsistenz (Graph == Konstante, Monotonie).

Verhindert die Wiederkehr des Graph(5,42)/Konstante(8,00)-Konflikts:
Kat-7 (Krankenhaus OP/Intensiv) muss die teuerste Kategorie sein und
Graph-Wert muss dem Python-Fallback entsprechen.
"""

from products.dguv_v3.merkmale import Installationskategorie
from products.dguv_v3.pricing_rules import PREIS_PER_10M2


class TestKat7Monotonie:
    def test_kat7_groesste_konstante(self):
        kat7 = PREIS_PER_10M2[Installationskategorie.KAT_7]
        assert kat7 == max(PREIS_PER_10M2.values())
        assert kat7 >= PREIS_PER_10M2[Installationskategorie.KAT_6]

    def test_graph_schema_stimmt_mit_konstante(self):
        # Statisch gegen die graph_schema-Definition (Quelle der FalkorDB-Nodes)
        import re
        from pathlib import Path
        schema = Path(__file__).parent.parent / "products/dguv_v3/graph_schema.py"
        text = schema.read_text(encoding="utf-8")
        m = re.search(r"\('KAT_7',\s*'[^']*',\s*([\d.]+),", text)
        assert m, "KAT_7-Zeile nicht im graph_schema gefunden"
        graph_rate = float(m.group(1))
        assert graph_rate == PREIS_PER_10M2[Installationskategorie.KAT_7], (
            f"Graph KAT_7={graph_rate} ≠ Konstante "
            f"{PREIS_PER_10M2[Installationskategorie.KAT_7]} (D-K7-Divergenz zurück!)")
