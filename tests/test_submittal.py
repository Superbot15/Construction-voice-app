from civil_ai.parsers import extract_text, parse_submittal


def test_example_cover(examples):
    sub = parse_submittal(extract_text(examples / "submittal_cover.txt"))
    assert sub.number == "03 30 00-004"
    assert sub.revision == "1"
    assert sub.spec_section == "03 30 00"
    assert sub.title.startswith("Concrete Mix Design")
    assert sub.status == "approved as noted"


def test_compact_section_number_and_status_in_body():
    sub = parse_submittal("Submittal #: 17\nSection: 312000\nREVISE AND RESUBMIT per comments.")
    assert sub.spec_section == "31 20 00"
    assert sub.status == "revise and resubmit"
