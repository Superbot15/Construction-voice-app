from civil_ai.parsers import extract_text, parse_product_data_sheet


def test_example_sheet(examples):
    pds = parse_product_data_sheet(extract_text(examples / "pds_concrete_mix.txt"), "pds")
    assert pds.product_name.startswith("StructuraMix 4500")
    assert pds.manufacturer.startswith("Example Aggregates")
    assert {"ASTM C94", "ASTM C150", "ASTM C494"} <= set(pds.standards)

    fc = pds.properties["compressive_strength_28_day"]
    assert (fc.value, fc.unit, fc.qualifier) == (4500.0, "psi", "min")
    assert pds.properties["air_content"].unit == "%"
    agg = pds.properties["maximum_aggregate_size"]
    assert agg.unit == "in" and round(agg.value, 2) == 0.75


def test_metric_sheet_is_normalized():
    pds = parse_product_data_sheet("Compressive Strength: 35 MPa\nFlexural Strength: 4.5 MPa\n")
    assert round(pds.properties["compressive_strength"].value) == 5076
    assert pds.properties["flexural_strength"].unit == "psi"


def test_prefix_qualifier():
    pds = parse_product_data_sheet("Tensile Strength: min. 60 ksi\n")
    m = pds.properties["tensile_strength"]
    assert (m.value, m.unit, m.qualifier) == (60000.0, "psi", "min")


def test_first_occurrence_wins():
    pds = parse_product_data_sheet("Slump: 4 in\nSlump: 9 in\n")
    assert pds.properties["slump"].value == 4.0


def test_aashto_and_aci_standards():
    pds = parse_product_data_sheet("Tested per AASHTO T 22 and placed per ACI 301.")
    assert "AASHTO T 22" in pds.standards
    assert "ACI 301" in pds.standards


def test_empty_text():
    pds = parse_product_data_sheet("")
    assert pds.properties == {} and pds.standards == []
