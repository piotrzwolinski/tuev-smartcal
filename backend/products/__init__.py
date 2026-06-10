"""Product registry.

Import side-effect: each submodule calls register_gewerk().
"""

from . import blitzschutz, rlt, dguv_v3  # noqa: F401

from engine.gewerk import list_gewerke, get_gewerk  # noqa: F401
