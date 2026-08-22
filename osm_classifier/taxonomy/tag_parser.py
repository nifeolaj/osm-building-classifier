"""Utilities for parsing serialized OSM tags."""

from __future__ import annotations

import ast
import json
import re
from typing import Any


def parse_tags(value: Any) -> dict[str, Any]:
    """Convert an OSM tags value into a dictionary."""
    if isinstance(value, dict):
        return value

    if value is None or not isinstance(value, str):
        return {}

    text = value.strip()
    if not text or text.lower() in {"{}", "nan", "none", "null"}:
        return {}

    try:
        parsed = json.loads(text)
        if isinstance(parsed, dict):
            return parsed
    except (json.JSONDecodeError, TypeError):
        pass

    try:
        parsed = ast.literal_eval(text)
        if isinstance(parsed, dict):
            return parsed
    except (ValueError, SyntaxError):
        pass

    pairs = re.findall(
        r"""['"]([^'"]+)['"]\s*:\s*['"]([^'"]*)['"]""",
        text,
    )
    return dict(pairs)