"""Product-agnostic Kalkulator engine.

Core abstraction: Gewerk = jedna jednostka kalkulacji (Blitzschutz / RLT / DGUV V3 / ...).
Dodanie nowego Gewerku = nowy folder w products/, 4 pliki (merkmale, pricing_rules, prompt, golden_set).
"""

from engine.gewerk import Gewerk, Angebot, Breakdown  # noqa: F401
