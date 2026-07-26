"""Thin public API for the tool bus.

Prefer importing from here for backward compatibility:
  from app.tools.registry import ToolExecutor, openrouter_tools_schema
"""

from __future__ import annotations

from app.tools.executor import ToolExecutor
from app.tools.handlers import HANDLERS
from app.tools.manifest import TOOL_META, assert_schema_alignment
from app.tools.schemas import openrouter_tools_schema, schema_tool_names

# Boot-time drift checks (import side effect — fail fast in tests/dev).
assert_schema_alignment(schema_tool_names())
_missing_handlers = set(TOOL_META) - set(HANDLERS)
_extra_handlers = set(HANDLERS) - set(TOOL_META)
if _missing_handlers or _extra_handlers:
    raise AssertionError(
        f"handler drift: missing={sorted(_missing_handlers)} "
        f"extra={sorted(_extra_handlers)}"
    )

__all__ = ["ToolExecutor", "openrouter_tools_schema"]
