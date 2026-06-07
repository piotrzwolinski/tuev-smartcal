"""Graph-as-Single-Source-of-Truth reader with Python fallback.

Every pricing rule lives in the graph. Python dicts are fallback only.
Logs a warning when fallback is used — means graph is missing data.
"""

import logging
import os
from typing import Any, Optional

from common.database import get_graph

log = logging.getLogger(__name__)

USE_GRAPH_PRICING = os.getenv("USE_GRAPH_PRICING", "true").lower() != "false"


class GraphReader:
    """Read values from FalkorDB graph with fallback to Python defaults."""

    def __init__(self, graph_name: str = "dguv_v3"):
        self._graph_name = graph_name
        self._cache: dict[str, Any] = {}

    def _graph(self):
        return get_graph(self._graph_name)

    def get(self, query: str, params: dict | None = None, fallback: Any = None, cache_key: str | None = None) -> Any:
        if not USE_GRAPH_PRICING:
            return fallback

        if cache_key and cache_key in self._cache:
            return self._cache[cache_key]

        try:
            result = self._graph().query(query, params=params or {}).result_set
            if result and result[0][0] is not None:
                value = result[0][0]
                if _plausible(value, fallback):
                    if cache_key:
                        self._cache[cache_key] = value
                    return value
                else:
                    log.error(f"Graph value {value} implausible (fallback={fallback}), query={query[:80]}")
                    return fallback
        except Exception as e:
            log.warning(f"Graph query failed: {e}, using fallback for {cache_key or query[:60]}")

        return fallback

    def get_row(self, query: str, params: dict | None = None, cache_key: str | None = None) -> list | None:
        if not USE_GRAPH_PRICING:
            return None

        if cache_key and cache_key in self._cache:
            return self._cache[cache_key]

        try:
            result = self._graph().query(query, params=params or {}).result_set
            if result:
                if cache_key:
                    self._cache[cache_key] = result[0]
                return result[0]
        except Exception as e:
            log.warning(f"Graph query failed: {e}")

        return None

    def get_all(self, query: str, params: dict | None = None) -> list[list]:
        if not USE_GRAPH_PRICING:
            return []

        try:
            result = self._graph().query(query, params=params or {}).result_set
            return result or []
        except Exception as e:
            log.warning(f"Graph query failed: {e}")
            return []

    def clear_cache(self):
        self._cache.clear()


def _plausible(value: Any, fallback: Any) -> bool:
    if fallback is None:
        return True
    if isinstance(value, (int, float)) and isinstance(fallback, (int, float)):
        if fallback == 0:
            return True
        if value <= 0:
            return False
        if value > abs(fallback) * 20:
            return False
    return True


_default_reader: Optional[GraphReader] = None


def get_reader(graph_name: str = "dguv_v3") -> GraphReader:
    global _default_reader
    if _default_reader is None or _default_reader._graph_name != graph_name:
        _default_reader = GraphReader(graph_name)
    return _default_reader
