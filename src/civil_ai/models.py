"""Structured records produced by the parsers."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field


@dataclass
class Measurement:
    name: str
    value: float
    unit: str
    raw: str = ""
    qualifier: str = ""  # "min" / "max" when the sheet states a limit, e.g. "4000 psi min"

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class ProductDataSheet:
    source: str
    product_name: str = ""
    manufacturer: str = ""
    standards: list[str] = field(default_factory=list)
    properties: dict[str, Measurement] = field(default_factory=dict)

    def to_dict(self) -> dict:
        d = asdict(self)
        d["properties"] = {k: v.to_dict() for k, v in self.properties.items()}
        return d


@dataclass
class Submittal:
    source: str
    number: str = ""
    revision: str = ""
    spec_section: str = ""
    title: str = ""
    contractor: str = ""
    date: str = ""
    status: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class FieldTest:
    name: str
    value: float
    unit: str
    location: str = ""
    raw: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class DailyLog:
    source: str
    date: str = ""
    inspector: str = ""
    weather: str = ""
    ambient_temp_f: float | None = None
    notes: list[str] = field(default_factory=list)
    tests: list[FieldTest] = field(default_factory=list)

    def to_dict(self) -> dict:
        d = asdict(self)
        d["tests"] = [t.to_dict() for t in self.tests]
        return d
