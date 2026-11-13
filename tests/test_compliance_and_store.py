from civil_ai.cli import main
from civil_ai.compliance import Requirement, check_daily_log, check_product_data, load_requirements
from civil_ai.parsers import extract_text, parse_daily_log, parse_product_data_sheet
from civil_ai.store import Store


def test_product_data_checks(examples):
    reqs = load_requirements(examples / "requirements.toml")
    pds = parse_product_data_sheet(extract_text(examples / "pds_concrete_mix.txt"), "pds")
    statuses = {f.requirement_id: f.status for f in check_product_data(pds, reqs)}
    assert statuses == {"03 30 00-2.2.A": "pass", "03 30 00-2.1.C": "pass"}


def test_metric_requirement_against_imperial_sheet():
    pds = parse_product_data_sheet("Compressive Strength: 4,000 psi")
    req = Requirement(id="r", property="compressive_strength", min=30, unit="MPa")
    assert check_product_data(pds, [req])[0].status == "fail"  # 30 MPa ~ 4351 psi


def test_missing_property():
    pds = parse_product_data_sheet("Slump: 4 in")
    req = Requirement(id="r", property="compressive_strength", min=4000, unit="psi")
    assert check_product_data(pds, [req])[0].status == "missing"


def test_daily_log_checks(examples):
    reqs = load_requirements(examples / "requirements.toml")
    log = parse_daily_log(extract_text(examples / "daily_log.txt"), "log")
    fails = [f for f in check_daily_log(log, reqs) if f.status == "fail"]
    messages = " | ".join(f.message for f in fails)
    assert len(fails) == 3, messages  # truck 2 slump, truck 2 air, compaction
    assert "slump 7.25" in messages and "compaction 93" in messages


def test_store_roundtrip(tmp_path, examples):
    store = Store(tmp_path / "t.db")
    log = parse_daily_log(extract_text(examples / "daily_log.txt"), "log")
    doc = store.add(log)
    store.add_findings(doc, check_daily_log(log, load_requirements(examples / "requirements.toml")))
    rows = store.query("SELECT value FROM field_tests WHERE name = ? ORDER BY value", ("slump",))
    assert [r["value"] for r in rows] == [4.5, 7.25]
    assert store.query("SELECT COUNT(*) AS n FROM findings WHERE status='fail'")[0]["n"] == 3
    store.close()


def test_cli_check_exit_code(examples, capsys):
    code = main(["check", str(examples / "requirements.toml"), str(examples / "daily_log.txt")])
    assert code == 1
    assert "[FAIL" in capsys.readouterr().out


def test_cli_ingest_and_query(tmp_path, examples, capsys):
    db = str(tmp_path / "c.db")
    files = [str(examples / n) for n in ("submittal_cover.txt", "pds_concrete_mix.txt", "daily_log.txt")]
    assert main(["ingest", "--db", db, *files]) == 0
    out = capsys.readouterr().out
    assert "as submittal" in out and "as product_data" in out and "as daily_log" in out
    assert main(["query", "--db", db, "SELECT spec_section FROM submittals"]) == 0
    assert "03 30 00" in capsys.readouterr().out
