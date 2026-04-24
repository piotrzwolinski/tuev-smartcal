"""Re-export Claude LLM client from root llm.py (Phase 1 compat).

TODO Phase 2: move full ClaudeLLM class here, deprecate root llm.py.
"""

from llm import ClaudeLLM, HAIKU_MODEL, MODEL, ToolCall  # noqa: F401
