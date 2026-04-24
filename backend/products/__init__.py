"""Product registry.

Import side-effect: każdy submodule wywołuje register_gewerk().
"""

from . import blitzschutz, rlt, dguv_v3  # noqa: F401

from engine.gewerk import list_gewerke, get_gewerk  # noqa: F401
