"""Rule-based compliance checking against project specification requirements.

Requirements are written in TOML, one ``[[requirement]]`` table per check::

    [[requirement]]
    id = "03 30 00-2.3.A"
    property = "compressive_strength_28_day"
    applies_to = "product_data"   # or "field_test"
    min = 4000
    unit = "psi"

Values are unit-normalized before comparison, so a requirement in MPa can be
checked against a data sheet in psi.
"""

from __future__ import annotations

import tomllib
from dataclasses import asdict, dataclass
from pathlib import Path

from civil_ai.models import DailyLog, ProductDataSheet
from civil_ai.units import normalize


@dataclass
class Requirement:
    id: str
    property: str
    applies_to: str = "product_data"
    min: float | None = None
    max: float | None = None
    unit: str = ""
    standard: str = ""  # required referenced standard, e.g. "ASTM C494"
    description: str = ""


@dataclass
class Finding:
    requirement_id: str
    source: str
    status: str  # "pass" | "fail" | "missing"
    message: str
    actual: float | None = None
    location: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


def load_requirements(path: str | Path) -> list[Requirement]:
    with open(path, "rb") as fh:
        data = tomllib.load(fh)
    return [Requirement(**r) for r in data.get("requirement", [])]


def _limits(req: Requirement) -> tuple[float | None, float | None, str]:
    lo = hi = None
    unit = req.unit
    if req.min is not None:
        lo, unit = normalize(req.min, req.unit)
    if req.max is not None:
        hi, unit = normalize(req.max, req.unit)
    return lo, hi, unit


def _compare(req: Requirement, value: float, unit: str, source: str, location: str = "") -> Finding:
    lo, hi, req_unit = _limits(req)
    if req_unit and unit != req_unit:
        return Finding(req.id, source, "fail", f"unit mismatch: got {unit}, need {req_unit}", value, location)
    if lo is not None and value < lo:
        return Finding(req.id, source, "fail", f"{req.property} {value} {unit} below minimum {lo}", value, location)
    if hi is not None and value > hi:
        return Finding(req.id, source, "fail", f"{req.property} {value} {unit} above maximum {hi}", value, location)
    return Finding(req.id, source, "pass", f"{req.property} {value} {unit} within limits", value, location)


def check_product_data(pds: ProductDataSheet, requirements: list[Requirement]) -> list[Finding]:
    findings: list[Finding] = []
    for req in requirements:
        if req.applies_to != "product_data":
            continue
        if req.standard:
            norm = req.standard.replace(" ", "").upper()
            ok = any(norm in s.replace(" ", "").upper() for s in pds.standards)
            findings.append(
                Finding(req.id, pds.source, "pass" if ok else "fail",
                        f"standard {req.standard} {'referenced' if ok else 'not referenced'}")
            )
            if not req.property:
                continue
        meas = pds.properties.get(req.property)
        if meas is None:
            findings.append(Finding(req.id, pds.source, "missing", f"{req.property} not stated on data sheet"))
            continue
        findings.append(_compare(req, meas.value, meas.unit, pds.source))
    return findings


def check_daily_log(log: DailyLog, requirements: list[Requirement]) -> list[Finding]:
    findings: list[Finding] = []
    for req in requirements:
        if req.applies_to != "field_test":
            continue
        tests = [t for t in log.tests if t.name == req.property]
        for t in tests:
            findings.append(_compare(req, t.value, t.unit, log.source, t.location))
    return findings
