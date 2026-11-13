"""SQLite store that makes parsed documents queryable with plain SQL."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from civil_ai.compliance import Finding
from civil_ai.models import DailyLog, ProductDataSheet, Submittal

SCHEMA = """
CREATE TABLE IF NOT EXISTS documents (
    id INTEGER PRIMARY KEY,
    source TEXT NOT NULL,
    kind TEXT NOT NULL,
    data TEXT NOT NULL,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS submittals (
    document_id INTEGER REFERENCES documents(id),
    number TEXT, revision TEXT, spec_section TEXT, title TEXT,
    contractor TEXT, date TEXT, status TEXT
);
CREATE TABLE IF NOT EXISTS properties (
    document_id INTEGER REFERENCES documents(id),
    product_name TEXT, manufacturer TEXT,
    name TEXT, value REAL, unit TEXT, qualifier TEXT
);
CREATE TABLE IF NOT EXISTS field_tests (
    document_id INTEGER REFERENCES documents(id),
    date TEXT, inspector TEXT, name TEXT, value REAL, unit TEXT, location TEXT
);
CREATE TABLE IF NOT EXISTS findings (
    document_id INTEGER REFERENCES documents(id),
    requirement_id TEXT, status TEXT, message TEXT, actual REAL, location TEXT
);
"""


class Store:
    def __init__(self, path: str | Path = "civil_ai.db"):
        self.conn = sqlite3.connect(str(path))
        self.conn.executescript(SCHEMA)

    def close(self) -> None:
        self.conn.close()

    def _doc(self, source: str, kind: str, data: dict) -> int:
        cur = self.conn.execute(
            "INSERT INTO documents (source, kind, data) VALUES (?, ?, ?)", (source, kind, json.dumps(data))
        )
        return int(cur.lastrowid)

    def add(self, record: Submittal | ProductDataSheet | DailyLog) -> int:
        with self.conn:
            if isinstance(record, Submittal):
                doc = self._doc(record.source, "submittal", record.to_dict())
                self.conn.execute(
                    "INSERT INTO submittals VALUES (?,?,?,?,?,?,?,?)",
                    (doc, record.number, record.revision, record.spec_section, record.title,
                     record.contractor, record.date, record.status),
                )
            elif isinstance(record, ProductDataSheet):
                doc = self._doc(record.source, "product_data", record.to_dict())
                self.conn.executemany(
                    "INSERT INTO properties VALUES (?,?,?,?,?,?,?)",
                    [(doc, record.product_name, record.manufacturer, m.name, m.value, m.unit, m.qualifier)
                     for m in record.properties.values()],
                )
            elif isinstance(record, DailyLog):
                doc = self._doc(record.source, "daily_log", record.to_dict())
                self.conn.executemany(
                    "INSERT INTO field_tests VALUES (?,?,?,?,?,?,?)",
                    [(doc, record.date, record.inspector, t.name, t.value, t.unit, t.location)
                     for t in record.tests],
                )
            else:
                raise TypeError(f"unsupported record: {type(record).__name__}")
        return doc

    def add_findings(self, document_id: int, findings: list[Finding]) -> None:
        with self.conn:
            self.conn.executemany(
                "INSERT INTO findings VALUES (?,?,?,?,?,?)",
                [(document_id, f.requirement_id, f.status, f.message, f.actual, f.location) for f in findings],
            )

    def query(self, sql: str, params: tuple = ()) -> list[dict]:
        cur = self.conn.execute(sql, params)
        cols = [c[0] for c in cur.description or []]
        return [dict(zip(cols, row)) for row in cur.fetchall()]
