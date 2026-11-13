from civil_ai.parsers import extract_text, parse_daily_log


def test_example_log(examples):
    log = parse_daily_log(extract_text(examples / "daily_log.txt"))
    assert log.date == "2026-10-14"
    assert log.inspector == "J. Doe"
    assert log.ambient_temp_f == 58.0

    slumps = [t.value for t in log.tests if t.name == "slump"]
    assert slumps == [4.5, 7.25]
    temps = [t for t in log.tests if t.name == "concrete_temperature"]
    assert [t.value for t in temps] == [68.0, 71.0]
    comp = [t for t in log.tests if t.name == "compaction"]
    assert comp[0].value == 93.0 and comp[0].location == "12+50"
    assert len(log.notes) == 2


def test_ambient_air_temp_is_not_air_content():
    log = parse_daily_log("Air Temp: 40 F\n")
    assert not [t for t in log.tests if t.name == "air_content"]
    assert log.ambient_temp_f == 40.0


def test_celsius_concrete_temp():
    log = parse_daily_log("Concrete Temp: 20 C\n")
    assert log.tests[0].value == 68.0 and log.tests[0].unit == "F"
