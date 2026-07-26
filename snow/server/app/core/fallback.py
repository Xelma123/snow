"""Backward-compatible alias — device actuator rules live in device_rules.py """

from app.core.device_rules import (  # noqa: F401
    split_intents,
    try_rule_fallback,
    _fold,
    _parse_delay_seconds,
)

__all__ = [
    "split_intents",
    "try_rule_fallback",
    "_fold",
    "_parse_delay_seconds",
]
