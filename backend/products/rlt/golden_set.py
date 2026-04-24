"""RLT golden set — TODO M3.3 (KW18).

Źródła:
- Vorlage Kalkulation sheet 'GT RLT' (47×10) + 'GT Hygiene' (46×10)
- MUC Preistool sheet 'VDI 6022' (80×11)

Nie mamy 1:1 Anlagen-to-Preis matchingu jak dla Blitzschutz StV.
Strategia: wyderywować ~150 reference cases z Vorlage-templates + MUC-realpreise.
"""

from typing import List, Tuple

from products.rlt.merkmale import RLTMerkmale


def load_rlt_golden_set() -> List[Tuple[RLTMerkmale, float, str]]:
    """STUB — implementacja w M3.3 (KW18)."""
    return []
