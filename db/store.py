"""SQLite store for runs, outputs, the golden dataset, and flagged outputs."""

import json
import os
import sqlite3
import threading
from datetime import datetime, timezone
from typing import Any, Optional

DEFAULT_SQLITE_PATH = os.getenv("SQLITE_PATH", "./agent.db")


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


class Store:
    """Local SQLite wrapper. One connection guarded by a lock so the API
    handlers and CLI can share a Store."""

    def __init__(self, path: str = DEFAULT_SQLITE_PATH):
        self.path = path
        self._lock = threading.Lock()
        self._conn = sqlite3.connect(path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL;")
        self._init_schema()

    def _init_schema(self) -> None:
        with self._lock, self._conn:
            self._conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS runs (
                    id              INTEGER PRIMARY KEY AUTOINCREMENT,
                    brief           TEXT NOT NULL,        -- JSON brand brief
                    prompt_version  TEXT NOT NULL,
                    timestamp       TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS outputs (
                    id                INTEGER PRIMARY KEY AUTOINCREMENT,
                    run_id            INTEGER NOT NULL,
                    variant_type      TEXT NOT NULL,      -- headline | body | cta
                    content           TEXT NOT NULL,
                    hook_strength     REAL,
                    brand_alignment   REAL,
                    clarity           REAL,
                    conversion_intent REAL,
                    weighted_average  REAL,
                    prompt_version    TEXT NOT NULL,
                    timestamp         TEXT NOT NULL,
                    FOREIGN KEY (run_id) REFERENCES runs(id)
                );

                CREATE TABLE IF NOT EXISTS golden (
                    id                INTEGER PRIMARY KEY AUTOINCREMENT,
                    brief             TEXT NOT NULL,
                    variant_type      TEXT NOT NULL,
                    output            TEXT NOT NULL,
                    hook_strength     REAL,
                    brand_alignment   REAL,
                    clarity           REAL,
                    conversion_intent REAL,
                    weighted_average  REAL NOT NULL,
                    prompt_version    TEXT NOT NULL,
                    timestamp         TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS flagged_outputs (
                    id                INTEGER PRIMARY KEY AUTOINCREMENT,
                    run_id            INTEGER,
                    brief             TEXT NOT NULL,
                    variant_type      TEXT NOT NULL,
                    output            TEXT NOT NULL,
                    weighted_average  REAL,
                    reason            TEXT NOT NULL,
                    timestamp         TEXT NOT NULL
                );
                """
            )

    def create_run(self, brief: dict[str, Any], prompt_version: str) -> int:
        with self._lock, self._conn:
            cur = self._conn.execute(
                "INSERT INTO runs (brief, prompt_version, timestamp) VALUES (?, ?, ?)",
                (json.dumps(brief), prompt_version, _utcnow()),
            )
            return int(cur.lastrowid)

    def get_run(self, run_id: int) -> Optional[dict[str, Any]]:
        with self._lock:
            row = self._conn.execute(
                "SELECT * FROM runs WHERE id = ?", (run_id,)
            ).fetchone()
        return dict(row) if row else None

    def add_output(
        self,
        run_id: int,
        variant_type: str,
        content: str,
        scores: dict[str, float],
        prompt_version: str,
    ) -> int:
        """Persist one generated variant together with its 4 dimension scores."""
        with self._lock, self._conn:
            cur = self._conn.execute(
                """
                INSERT INTO outputs (
                    run_id, variant_type, content,
                    hook_strength, brand_alignment, clarity, conversion_intent,
                    weighted_average, prompt_version, timestamp
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    run_id,
                    variant_type,
                    content,
                    scores.get("hook_strength"),
                    scores.get("brand_alignment"),
                    scores.get("clarity"),
                    scores.get("conversion_intent"),
                    scores.get("weighted_average"),
                    prompt_version,
                    _utcnow(),
                ),
            )
            return int(cur.lastrowid)

    def get_outputs_for_run(self, run_id: int) -> list[dict[str, Any]]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT * FROM outputs WHERE run_id = ? ORDER BY id", (run_id,)
            ).fetchall()
        return [dict(r) for r in rows]

    def add_golden(
        self,
        brief: dict[str, Any],
        variant_type: str,
        output: str,
        scores: dict[str, float],
        prompt_version: str,
    ) -> int:
        with self._lock, self._conn:
            cur = self._conn.execute(
                """
                INSERT INTO golden (
                    brief, variant_type, output,
                    hook_strength, brand_alignment, clarity, conversion_intent,
                    weighted_average, prompt_version, timestamp
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    json.dumps(brief),
                    variant_type,
                    output,
                    scores.get("hook_strength"),
                    scores.get("brand_alignment"),
                    scores.get("clarity"),
                    scores.get("conversion_intent"),
                    scores.get("weighted_average"),
                    prompt_version,
                    _utcnow(),
                ),
            )
            return int(cur.lastrowid)

    def get_golden(self) -> list[dict[str, Any]]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT * FROM golden ORDER BY id"
            ).fetchall()
        result = []
        for r in rows:
            d = dict(r)
            d["brief"] = json.loads(d["brief"])
            result.append(d)
        return result

    def golden_exists(self, brief: dict[str, Any], variant_type: str, output: str) -> bool:
        """Avoid inserting an identical golden entry twice."""
        with self._lock:
            row = self._conn.execute(
                "SELECT 1 FROM golden WHERE brief = ? AND variant_type = ? AND output = ? LIMIT 1",
                (json.dumps(brief), variant_type, output),
            ).fetchone()
        return row is not None

    def add_flagged(
        self,
        brief: dict[str, Any],
        variant_type: str,
        output: str,
        weighted_average: Optional[float],
        reason: str,
        run_id: Optional[int] = None,
    ) -> int:
        with self._lock, self._conn:
            cur = self._conn.execute(
                """
                INSERT INTO flagged_outputs (
                    run_id, brief, variant_type, output, weighted_average, reason, timestamp
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    run_id,
                    json.dumps(brief),
                    variant_type,
                    output,
                    weighted_average,
                    reason,
                    _utcnow(),
                ),
            )
            return int(cur.lastrowid)

    def get_flagged(self) -> list[dict[str, Any]]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT * FROM flagged_outputs ORDER BY id"
            ).fetchall()
        result = []
        for r in rows:
            d = dict(r)
            d["brief"] = json.loads(d["brief"])
            result.append(d)
        return result

    def count_runs(self) -> int:
        with self._lock:
            row = self._conn.execute("SELECT COUNT(*) AS n FROM runs").fetchone()
        return int(row["n"])

    def count_golden(self) -> int:
        with self._lock:
            row = self._conn.execute("SELECT COUNT(*) AS n FROM golden").fetchone()
        return int(row["n"])

    def count_flagged(self) -> int:
        with self._lock:
            row = self._conn.execute("SELECT COUNT(*) AS n FROM flagged_outputs").fetchone()
        return int(row["n"])

    def close(self) -> None:
        with self._lock:
            self._conn.close()
