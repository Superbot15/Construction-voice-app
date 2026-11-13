# Contributing to Civil AI

Thanks for helping. Field engineers, inspectors, PMs and developers are all welcome.

## Most useful contributions

1. **Sample documents.** Anonymized submittal covers, product data sheets and daily logs whose layouts the parsers don't handle yet. Remove names, project numbers and anything confidential first. Never submit documents you aren't allowed to share.
2. **Parser tests.** Each new layout should come with a test in `tests/` that pins the fields we expect to extract.
3. **Units and test types.** New quantities in `src/civil_ai/units.py`, new field tests in `src/civil_ai/parsers/daily_log.py`.

## Development

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev,pdf]"
pytest
ruff check .
```

Open an issue before large changes so we can agree on direction. Keep pull requests focused and include tests.
