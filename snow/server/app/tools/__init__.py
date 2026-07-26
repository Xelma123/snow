"""Snow tools package.

Import from submodules directly, e.g.:
  from app.tools.registry import ToolExecutor
  from app.tools.routines import list_routine_summaries

Do not eagerly import registry here — it creates a circular import with
core.context → tools.routines → tools.__init__ → registry → executor → context.
"""

__all__: list[str] = []
