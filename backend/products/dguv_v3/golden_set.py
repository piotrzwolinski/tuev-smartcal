"""DGUV V3 golden set — TODO M3.4 (KW18).

Źródła:
- Gersthofen (1,393 pozycji LV w `Pruefung Elektrische Anlagen_Stadt Gersthofen.xlsm`)
  = edge case Verteiler-Ebene
- Audi 059E-2025 Ausschreibung (GAEB-Konverter format, 74×48 cells)
  = real Ausschreibung format

~50 reference cases. Walidacja target: match_rate@±15% ≥ 70%.
"""

from typing import List, Tuple

from products.dguv_v3.merkmale import DGUVMerkmale


def load_dguv_golden_set() -> List[Tuple[DGUVMerkmale, float, str]]:
    """STUB — implementacja w M3.4 (KW18)."""
    return []
