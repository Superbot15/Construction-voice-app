from __future__ import annotations

import re

NUMBER = r"(-?\d{1,3}(?:,\d{3})+(?:\.\d+)?|-?\d+(?:\.\d+)?)"
UNIT = r"(psi|ksi|mpa|kpa|°\s?[fc]|deg\s?[fc]|[fc]\b|%|percent|pcf|lb/ft3|kg/m3|inches|inch|in\.?|mm|cm|ft|minutes|min|hours|hr|\")"


def slug(text: str) -> str:
    """'Compressive Strength (28-day)' -> 'compressive_strength_28_day'."""
    return re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")


def field(text: str, *labels: str) -> str:
    """Return the value after the first ``Label:`` match among ``labels``."""
    for label in labels:
        m = re.search(rf"^\s*{label}\s*[:#\-]\s*(.+?)\s*$", text, re.IGNORECASE | re.MULTILINE)
        if m:
            return m.group(1).strip()
    return ""
