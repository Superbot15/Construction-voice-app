"""Product data sheet (PDS) / material data sheet parser.

Pulls product name, manufacturer, referenced standards (ASTM, AASHTO, ACI)
and "Property ..... value unit" lines into normalized measurements.
"""

from __future__ import annotations

import re

from civil_ai.models import Measurement, ProductDataSheet
from civil_ai.parsers._common import NUMBER, UNIT, field, slug
from civil_ai.units import normalize, parse_number

STANDARD_RE = re.compile(r"\b(ASTM\s?[A-Z]\s?\d+(?:/[A-Z]\d+)?M?|AASHTO\s?[MT]\s?\d+|ACI\s?\d{3}(?:\.\d+)?R?)\b")

PROPERTY_RE = re.compile(
    rf"^\s*(?P<name>[A-Za-z][A-Za-z0-9 ()/,\-]*?)\s*(?:[:=]|\.{{2,}}|\s{{2,}}|\t)\s*"
    rf"(?P<qual_pre>(?:min(?:imum)?|max(?:imum)?)\.?\s+)?"
    rf"(?P<num>{NUMBER})\s*(?P<unit>{UNIT})"
    rf"(?:\s*(?P<qual_post>min(?:imum)?|max(?:imum)?)\.?)?",
    re.IGNORECASE | re.MULTILINE,
)


def parse_product_data_sheet(text: str, source: str = "") -> ProductDataSheet:
    pds = ProductDataSheet(source=source)
    pds.product_name = field(text, "Product(?: Name)?", "Material")
    pds.manufacturer = field(text, "Manufacturer", "Supplier", "Mfr")
    pds.standards = sorted({re.sub(r"\s+", " ", s) for s in STANDARD_RE.findall(text)})

    for m in PROPERTY_RE.finditer(text):
        name = slug(m.group("name"))
        if not name or name in pds.properties:
            continue
        value, unit = normalize(parse_number(m.group("num")), m.group("unit"))
        qual = (m.group("qual_pre") or m.group("qual_post") or "").strip().lower()[:3]
        pds.properties[name] = Measurement(
            name=name, value=value, unit=unit, raw=m.group(0).strip(), qualifier=qual
        )
    return pds
