"""Submittal cover sheet / transmittal parser."""

from __future__ import annotations

import re

from civil_ai.models import Submittal
from civil_ai.parsers._common import field

# CSI MasterFormat section, e.g. "03 30 00" or "033000" or "03 30 00.13"
SPEC_RE = re.compile(r"\b(\d{2})\s?(\d{2})\s?(\d{2})(\.\d{2})?\b")

STATUSES = (
    "approved as noted",
    "revise and resubmit",
    "no exceptions taken",
    "approved",
    "rejected",
    "for record only",
)


def parse_submittal(text: str, source: str = "") -> Submittal:
    sub = Submittal(source=source)
    sub.number = field(text, r"Submittal\s*(?:No\.?|Number|#)", "Transmittal No\\.?")
    sub.revision = field(text, r"Rev(?:ision)?\.?")
    sub.title = field(text, "Title", "Description", "Subject")
    sub.contractor = field(text, "Contractor", "Submitted By", "From")
    sub.date = field(text, "Date(?: Submitted)?")
    sub.status = field(text, "Status", "Action", "Review Action").lower()
    if not sub.status:
        low = text.lower()
        sub.status = next((s for s in STATUSES if s in low), "")

    section = field(text, r"Spec(?:ification)?\s*Section", "Section")
    m = SPEC_RE.search(section or text)
    if m:
        sub.spec_section = f"{m.group(1)} {m.group(2)} {m.group(3)}{m.group(4) or ''}"
    return sub
