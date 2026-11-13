import pytest

from civil_ai.units import normalize, parse_number


def test_mpa_to_psi():
    value, unit = normalize(30, "MPa")
    assert unit == "psi"
    assert value == pytest.approx(4351.1, rel=1e-3)


def test_celsius_to_fahrenheit():
    assert normalize(20, "°C") == (68.0, "F")


def test_mm_to_inches():
    value, unit = normalize(25.4, "mm")
    assert (round(value, 3), unit) == (1.0, "in")


def test_unknown_unit_passes_through():
    assert normalize(3, "bags") == (3, "bags")


def test_parse_number_with_thousands_separator():
    assert parse_number("4,500") == 4500.0
