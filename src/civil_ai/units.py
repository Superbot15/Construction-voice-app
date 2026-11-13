"""Unit normalization for common heavy civil quantities.

Every quantity is converted to a canonical unit so that values parsed from
different documents (one in MPa, one in psi) can be compared directly.
"""

from __future__ import annotations

import re

# alias -> (canonical unit, multiplier, offset); canonical = value * mult + offset
_CONVERSIONS: dict[str, tuple[str, float, float]] = {
    "psi": ("psi", 1.0, 0.0),
    "ksi": ("psi", 1000.0, 0.0),
    "mpa": ("psi", 145.0377, 0.0),
    "kpa": ("psi", 0.1450377, 0.0),
    "in": ("in", 1.0, 0.0),
    "inch": ("in", 1.0, 0.0),
    "inches": ("in", 1.0, 0.0),
    '"': ("in", 1.0, 0.0),
    "mm": ("in", 1 / 25.4, 0.0),
    "cm": ("in", 1 / 2.54, 0.0),
    "ft": ("ft", 1.0, 0.0),
    "m": ("ft", 3.28084, 0.0),
    "%": ("%", 1.0, 0.0),
    "percent": ("%", 1.0, 0.0),
    "pcf": ("pcf", 1.0, 0.0),
    "lb/ft3": ("pcf", 1.0, 0.0),
    "kg/m3": ("pcf", 0.062428, 0.0),
    "f": ("F", 1.0, 0.0),
    "°f": ("F", 1.0, 0.0),
    "degf": ("F", 1.0, 0.0),
    "c": ("F", 1.8, 32.0),
    "°c": ("F", 1.8, 32.0),
    "degc": ("F", 1.8, 32.0),
    "min": ("min", 1.0, 0.0),
    "minutes": ("min", 1.0, 0.0),
    "hr": ("min", 60.0, 0.0),
    "hours": ("min", 60.0, 0.0),
}


def canonical_unit(unit: str) -> str | None:
    entry = _CONVERSIONS.get(_clean(unit))
    return entry[0] if entry else None


def normalize(value: float, unit: str) -> tuple[float, str]:
    """Convert ``value`` in ``unit`` to its canonical unit.

    Unknown units are passed through unchanged so nothing is silently lost.
    """
    entry = _CONVERSIONS.get(_clean(unit))
    if entry is None:
        return value, unit.strip()
    canon, mult, offset = entry
    return round(value * mult + offset, 4), canon


def parse_number(text: str) -> float:
    """Parse numbers such as ``4,500`` or ``0.45``."""
    return float(text.replace(",", "").strip())


def _clean(unit: str) -> str:
    return re.sub(r"\s+", "", unit.strip().lower()).rstrip(".")
