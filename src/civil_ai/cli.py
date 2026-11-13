"""Command line interface: ``civil-ai parse | ingest | check | query``."""

from __future__ import annotations

import argparse
import json
import sys

from civil_ai import __version__
from civil_ai.compliance import check_daily_log, check_product_data, load_requirements
from civil_ai.parsers import extract_text, parse_daily_log, parse_product_data_sheet, parse_submittal
from civil_ai.store import Store

PARSERS = {
    "submittal": parse_submittal,
    "product_data": parse_product_data_sheet,
    "daily_log": parse_daily_log,
}


def detect_kind(text: str) -> str:
    low = text.lower()
    if "submittal" in low or "transmittal" in low:
        return "submittal"
    if "inspector" in low or "daily report" in low or "daily log" in low:
        return "daily_log"
    return "product_data"


def _parse(path: str, kind: str | None):
    text = extract_text(path)
    kind = kind or detect_kind(text)
    return kind, PARSERS[kind](text, source=path)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="civil-ai", description=__doc__)
    ap.add_argument("--version", action="version", version=f"civil-ai {__version__}")
    sub = ap.add_subparsers(dest="cmd", required=True)

    kind_help = "document type (auto-detected when omitted)"
    p = sub.add_parser("parse", help="parse documents and print JSON")
    p.add_argument("files", nargs="+")
    p.add_argument("--kind", choices=PARSERS, help=kind_help)

    i = sub.add_parser("ingest", help="parse documents into a SQLite database")
    i.add_argument("files", nargs="+")
    i.add_argument("--kind", choices=PARSERS, help=kind_help)
    i.add_argument("--db", default="civil_ai.db")
    i.add_argument("--requirements", help="TOML requirements file to check while ingesting")

    c = sub.add_parser("check", help="check documents against spec requirements")
    c.add_argument("requirements")
    c.add_argument("files", nargs="+")
    c.add_argument("--kind", choices=PARSERS, help=kind_help)

    q = sub.add_parser("query", help="run SQL against the database")
    q.add_argument("sql")
    q.add_argument("--db", default="civil_ai.db")

    args = ap.parse_args(argv)

    if args.cmd == "parse":
        out = [_parse(f, args.kind)[1].to_dict() for f in args.files]
        print(json.dumps(out if len(out) > 1 else out[0], indent=2))
        return 0

    if args.cmd == "check":
        reqs = load_requirements(args.requirements)
        failed = False
        for f in args.files:
            kind, rec = _parse(f, args.kind)
            findings = (check_product_data(rec, reqs) if kind == "product_data"
                        else check_daily_log(rec, reqs) if kind == "daily_log" else [])
            for fd in findings:
                failed |= fd.status != "pass"
                loc = f" @ {fd.location}" if fd.location else ""
                print(f"[{fd.status.upper():7}] {fd.requirement_id}: {fd.message}{loc}  ({f})")
        return 1 if failed else 0

    if args.cmd == "ingest":
        store = Store(args.db)
        reqs = load_requirements(args.requirements) if args.requirements else []
        for f in args.files:
            kind, rec = _parse(f, args.kind)
            doc = store.add(rec)
            if reqs and kind in ("product_data", "daily_log"):
                check = check_product_data if kind == "product_data" else check_daily_log
                store.add_findings(doc, check(rec, reqs))
            print(f"ingested {f} as {kind} (document {doc})")
        store.close()
        return 0

    if args.cmd == "query":
        store = Store(args.db)
        print(json.dumps(store.query(args.sql), indent=2))
        store.close()
        return 0
    return 2


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
