# Civil AI

**Open-source document intelligence for heavy civil construction.**

Civil AI turns submittal packages, product and material data sheets, and daily inspector logs into structured,
queryable data. It then checks that data against your project specifications automatically.

> **Status: pre-release (0.1.0).** This is a brand-new project. The core parsers, compliance engine and CLI work and
> are tested, but layouts in the wild vary a lot. Feedback and anonymized sample documents are the most valuable
> contributions right now. See [CONTRIBUTING.md](CONTRIBUTING.md).

## Why

Submittal review and field QA still happen mostly by hand: an engineer reads a data sheet, finds the spec paragraph,
compares numbers, and logs the result. Inspector reports hold test results that rarely make it into anything
searchable. General-purpose AI tools don't understand CSI sections, ASTM references or field test limits, and
commercial construction platforms keep this data inside their own systems.

Civil AI is a small, transparent, local-first alternative:

- **Runs offline.** No network calls and no runtime dependencies beyond the Python standard library (PDF support is
  an optional extra). Built for jobsite trailers with poor connectivity.
- **Unit-aware.** psi/MPa, °F/°C, in/mm and more are normalized before any comparison.
- **Plain SQLite output.** Query your documents with SQL, or point any BI tool at the database.
- **Spec requirements as code.** Requirements live in reviewable TOML files that you can version alongside the project.

## What it extracts

| Document | Fields |
|---|---|
| Submittal cover / transmittal | number, revision, CSI spec section, title, contractor, date, review status |
| Product / material data sheet | product, manufacturer, referenced standards (ASTM, AASHTO, ACI), every `property … value unit` line |
| Daily inspector log | date, inspector, weather, ambient temp, slump, air content, concrete temp, unit weight, compaction, location/station, notes |

## Quick start

```bash
pip install "civil-ai[pdf] @ git+https://github.com/superbot15/construction-voice-app"   # PyPI release coming
cd examples
civil-ai check requirements.toml pds_concrete_mix.txt daily_log.txt
```

```text
[PASS   ] 03 30 00-2.2.A: compressive_strength_28_day 4500.0 psi within limits  (pds_concrete_mix.txt)
[PASS   ] 03 30 00-2.1.C: standard ASTM C494 referenced  (pds_concrete_mix.txt)
[PASS   ] 03 30 00-3.4.B slump: slump 4.5 in within limits @ Pier 3  (daily_log.txt)
[FAIL   ] 03 30 00-3.4.B slump: slump 7.25 in above maximum 5.0 @ Pier 3  (daily_log.txt)
[PASS   ] 03 30 00-3.4.B air: air_content 5.8 % within limits @ Pier 3  (daily_log.txt)
[FAIL   ] 03 30 00-3.4.B air: air_content 4.1 % below minimum 5.0 @ Pier 3  (daily_log.txt)
[PASS   ] 03 30 00-3.5 temp: concrete_temperature 68.0 F within limits @ Pier 3  (daily_log.txt)
[PASS   ] 03 30 00-3.5 temp: concrete_temperature 71.0 F within limits @ Pier 3  (daily_log.txt)
[FAIL   ] 31 23 23-3.3 compaction: compaction 93.0 % below minimum 95.0 @ 12+50  (daily_log.txt)
```

`check` exits with status 1 when anything fails, so it can gate an automated review.

### Build a queryable database

```bash
civil-ai ingest --db project.db --requirements requirements.toml *.txt
civil-ai query --db project.db "SELECT name, value, unit, location FROM field_tests WHERE name = 'slump'"
civil-ai query --db project.db "SELECT * FROM findings WHERE status != 'pass'"
```

Tables: `documents`, `submittals`, `properties`, `field_tests`, `findings`.

### Inspect what the parser sees

```bash
civil-ai parse pds_concrete_mix.txt
```

### Use it as a library

```python
from civil_ai.parsers import extract_text, parse_product_data_sheet
from civil_ai.compliance import load_requirements, check_product_data

pds = parse_product_data_sheet(extract_text("data_sheet.pdf"), source="data_sheet.pdf")
for finding in check_product_data(pds, load_requirements("requirements.toml")):
    print(finding.status, finding.message)
```

## Writing requirements

```toml
[[requirement]]
id = "03 30 00-2.2.A"
applies_to = "product_data"
property = "compressive_strength_28_day"
min = 30
unit = "MPa"     # compared correctly against a sheet that says "4,500 psi"
```

The full format is in [docs/requirements-format.md](docs/requirements-format.md).

## Limitations

- Parsing is rule-based. Clean, text-based PDFs and typed logs work best. Scanned documents need OCR first, and
  multi-column tables aren't handled yet.
- Civil AI assists reviewers. It does not replace engineering judgment or the engineer of record.

## Roadmap

Offline local LLM extraction for jobsite trailers, a much larger test suite for data sheet parsers, and enterprise
deployment documentation. Details are in [ROADMAP.md](ROADMAP.md).

## Development

```bash
pip install -e ".[dev,pdf]"
pytest
ruff check .
```

## License

[Apache 2.0](LICENSE)
