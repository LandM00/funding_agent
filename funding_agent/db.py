import json
import os
import sqlite3
from pathlib import Path
from typing import Iterable, List, Any

from funding_agent.models import FundingCall


try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
except ImportError:
    psycopg2 = None
    RealDictCursor = None


SQLITE_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS funding_calls (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source TEXT NOT NULL,
    source_url TEXT NOT NULL UNIQUE,
    call_id TEXT,
    title TEXT NOT NULL,
    summary TEXT,
    program TEXT,
    opening_date TEXT,
    deadline_date TEXT,
    budget_total REAL,
    funding_type TEXT,
    record_type TEXT DEFAULT 'call',
    why_relevant TEXT,
    eligible_entities TEXT,
    countries TEXT,
    topics TEXT,
    raw_text TEXT,
    relevance_score REAL DEFAULT 0
);
"""

POSTGRES_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS funding_calls (
    id SERIAL PRIMARY KEY,
    source TEXT NOT NULL,
    source_url TEXT NOT NULL UNIQUE,
    call_id TEXT,
    title TEXT NOT NULL,
    summary TEXT,
    program TEXT,
    opening_date TEXT,
    deadline_date TEXT,
    budget_total DOUBLE PRECISION,
    funding_type TEXT,
    record_type TEXT DEFAULT 'call',
    why_relevant TEXT,
    eligible_entities TEXT,
    countries TEXT,
    topics TEXT,
    raw_text TEXT,
    relevance_score DOUBLE PRECISION DEFAULT 0
);
"""

SQLITE_NOTIFIED_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS notified_calls (
    source_url TEXT PRIMARY KEY,
    notified_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""

POSTGRES_NOTIFIED_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS notified_calls (
    source_url TEXT PRIMARY KEY,
    notified_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);
"""


def _is_postgres_url(value: str | None) -> bool:
    if not value:
        return False

    lowered = value.lower()
    return lowered.startswith("postgresql://") or lowered.startswith("postgres://")


def _normalize_postgres_url(value: str) -> str:
    if value.startswith("postgres://"):
        return value.replace("postgres://", "postgresql://", 1)
    return value


class FundingDB:
    """
    Database wrapper compatibile con:
    - SQLite locale: FundingDB("funding_calls.db")
    - PostgreSQL/Supabase cloud: FundingDB("postgresql://...")
    """

    def __init__(self, db_path: str | None = None):
        database_url = os.getenv("DATABASE_URL")

        self.db_identifier = database_url or db_path or "funding_calls.db"
        self.is_postgres = _is_postgres_url(self.db_identifier)

        if self.is_postgres:
            if psycopg2 is None:
                raise RuntimeError(
                    "psycopg2-binary non è installato. "
                    "Installa con: pip install psycopg2-binary"
                )

            self.conn = psycopg2.connect(
                _normalize_postgres_url(self.db_identifier),
                cursor_factory=RealDictCursor,
            )
            self._execute(POSTGRES_SCHEMA_SQL)
            self._execute(POSTGRES_NOTIFIED_SCHEMA_SQL)
            self.conn.commit()

        else:
            self.db_path = Path(self.db_identifier)
            self.conn = sqlite3.connect(self.db_path)
            self.conn.row_factory = sqlite3.Row
            self._execute(SQLITE_SCHEMA_SQL)
            self._execute(SQLITE_NOTIFIED_SCHEMA_SQL)
            self.conn.commit()

    def _execute(self, sql: str, params: tuple | None = None):
        cur = self.conn.cursor()
        cur.execute(sql, params or ())
        return cur

    def _executemany(self, sql: str, rows: list[tuple]):
        cur = self.conn.cursor()
        cur.executemany(sql, rows)
        return cur

    def _placeholder(self) -> str:
        return "%s" if self.is_postgres else "?"

    def upsert_calls(self, calls: Iterable[FundingCall]) -> None:
        calls = list(calls)

        if not calls:
            return

        rows = []
        for call in calls:
            rows.append(
                (
                    call.source,
                    call.source_url,
                    call.call_id,
                    call.title,
                    call.summary,
                    call.program,
                    call.opening_date,
                    call.deadline_date,
                    call.budget_total,
                    call.funding_type,
                    call.record_type,
                    json.dumps(call.why_relevant, ensure_ascii=False),
                    json.dumps(call.eligible_entities, ensure_ascii=False),
                    json.dumps(call.countries, ensure_ascii=False),
                    json.dumps(call.topics, ensure_ascii=False),
                    call.raw_text,
                    call.relevance_score,
                )
            )

        if self.is_postgres:
            sql = """
            INSERT INTO funding_calls (
                source, source_url, call_id, title, summary, program,
                opening_date, deadline_date, budget_total, funding_type,
                record_type, why_relevant, eligible_entities, countries, topics,
                raw_text, relevance_score
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
            )
            ON CONFLICT(source_url) DO UPDATE SET
                source=EXCLUDED.source,
                call_id=EXCLUDED.call_id,
                title=EXCLUDED.title,
                summary=EXCLUDED.summary,
                program=EXCLUDED.program,
                opening_date=EXCLUDED.opening_date,
                deadline_date=EXCLUDED.deadline_date,
                budget_total=EXCLUDED.budget_total,
                funding_type=EXCLUDED.funding_type,
                record_type=EXCLUDED.record_type,
                why_relevant=EXCLUDED.why_relevant,
                eligible_entities=EXCLUDED.eligible_entities,
                countries=EXCLUDED.countries,
                topics=EXCLUDED.topics,
                raw_text=EXCLUDED.raw_text,
                relevance_score=EXCLUDED.relevance_score
            """
        else:
            sql = """
            INSERT INTO funding_calls (
                source, source_url, call_id, title, summary, program,
                opening_date, deadline_date, budget_total, funding_type,
                record_type, why_relevant, eligible_entities, countries, topics,
                raw_text, relevance_score
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(source_url) DO UPDATE SET
                source=excluded.source,
                call_id=excluded.call_id,
                title=excluded.title,
                summary=excluded.summary,
                program=excluded.program,
                opening_date=excluded.opening_date,
                deadline_date=excluded.deadline_date,
                budget_total=excluded.budget_total,
                funding_type=excluded.funding_type,
                record_type=excluded.record_type,
                why_relevant=excluded.why_relevant,
                eligible_entities=excluded.eligible_entities,
                countries=excluded.countries,
                topics=excluded.topics,
                raw_text=excluded.raw_text,
                relevance_score=excluded.relevance_score
            """

        self._executemany(sql, rows)
        self.conn.commit()

    def get_top_calls(self, limit: int = 100) -> List[Any]:
        placeholder = self._placeholder()

        cur = self._execute(
            f"""
            SELECT * FROM funding_calls
            ORDER BY
                CASE
                    WHEN record_type = 'call' THEN 0
                    WHEN record_type = 'support_doc' THEN 1
                    WHEN record_type = 'hub' THEN 2
                    ELSE 3
                END,
                relevance_score DESC,
                id DESC
            LIMIT {placeholder}
            """,
            (limit,),
        )
        return cur.fetchall()

    def get_top_real_calls(self, limit: int = 100) -> List[Any]:
        placeholder = self._placeholder()

        cur = self._execute(
            f"""
            SELECT * FROM funding_calls
            WHERE record_type = 'call'
            ORDER BY relevance_score DESC, id DESC
            LIMIT {placeholder}
            """,
            (limit,),
        )
        return cur.fetchall()

    def get_all_real_calls(self) -> List[Any]:
        cur = self._execute(
            """
            SELECT * FROM funding_calls
            WHERE record_type = 'call'
            ORDER BY relevance_score DESC, id DESC
            """
        )
        return cur.fetchall()

    def get_unnotified_real_calls(self, min_score: float = 0.0) -> List[Any]:
        placeholder = self._placeholder()

        cur = self._execute(
            f"""
            SELECT fc.*
            FROM funding_calls fc
            LEFT JOIN notified_calls nc
              ON fc.source_url = nc.source_url
            WHERE fc.record_type = 'call'
              AND fc.relevance_score >= {placeholder}
              AND nc.source_url IS NULL
            ORDER BY fc.relevance_score DESC, fc.id DESC
            """,
            (min_score,),
        )
        return cur.fetchall()

    def mark_calls_notified(self, source_urls: List[str]) -> None:
        if not source_urls:
            return

        if self.is_postgres:
            sql = """
            INSERT INTO notified_calls (source_url)
            VALUES (%s)
            ON CONFLICT(source_url) DO NOTHING
            """
        else:
            sql = """
            INSERT OR IGNORE INTO notified_calls (source_url)
            VALUES (?)
            """

        self._executemany(sql, [(url,) for url in source_urls])
        self.conn.commit()

    def close(self) -> None:
        self.conn.close()