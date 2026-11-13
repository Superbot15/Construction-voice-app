"""Daily inspector log / daily report parser.

Recognizes header fields and common field tests: slump, air content,
concrete temperature, unit weight and compaction (percent of max density).
"""

from __future__ import annotations

import re

from civil_ai.models import DailyLog, FieldTest
from civil_ai.parsers._common import NUMBER, field
from civil_ai.units import normalize, parse_number

TESTS = {
    "slump": (r"slump", "in"),
    "air_content": (r"air(?:\s+content)?", "%"),
    "concrete_temperature": (r"(?:concrete|mix)\s+temp(?:erature)?", "F"),
    "unit_weight": (r"unit\s+weight|density\s+\(fresh\)", "pcf"),
    "compaction": (r"compaction|relative\s+compaction|%\s*proctor", "%"),
}

LOC_RE = re.compile(r"(?:@|at|sta\.?|station)\s*([0-9]+\+[0-9.]+|[A-Za-z0-9\- ]{2,30}?)(?=[,;)]|$)", re.IGNORECASE)


def parse_daily_log(text: str, source: str = "") -> DailyLog:
    log = DailyLog(source=source)
    log.date = field(text, "Date")
    log.inspector = field(text, "Inspector", "Inspected By", "Prepared By")
    log.weather = field(text, "Weather", "Conditions")

    temp = re.search(rf"(?:ambient|air)\s+temp(?:erature)?\s*[:=]?\s*{NUMBER}\s*°?\s*([FC])\b", text, re.IGNORECASE)
    if temp:
        log.ambient_temp_f, _ = normalize(parse_number(temp.group(1)), temp.group(2))

    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        found = False
        for name, (label, default_unit) in TESTS.items():
            m = re.search(
                rf"\b(?:{label})\b\s*[:=]?\s*{NUMBER}\s*(°\s?[FC]|[FC]\b|%|in\.?|inches|mm|pcf)?",
                stripped,
                re.IGNORECASE,
            )
            if not m:
                continue
            if name == "air_content" and re.search(r"ambient|air\s+temp", stripped, re.IGNORECASE):
                continue
            value, unit = normalize(parse_number(m.group(1)), m.group(2) or default_unit)
            loc = LOC_RE.search(stripped)
            log.tests.append(
                FieldTest(name=name, value=value, unit=unit, location=loc.group(1).strip() if loc else "", raw=stripped)
            )
            found = True
        if not found and stripped.startswith(("-", "*", "•")):
            log.notes.append(stripped.lstrip("-*• ").strip())
    return log
