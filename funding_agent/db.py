import json
import sqlite3
from pathlib import Path
from typing import Iterable, List

from funding_agent.models import FundingCall


SCHEMA_SQL = """
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

NOTIFIED_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS notified_calls (
    source_url TEXT PRIMARY KEY,
    notified_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""


class FundingDB:
    def __init__(self, db_path: str):
        self.db_path = Path(db_path)
        self.conn = sqlite3.connect(self.db_path)
        self.conn.execute(SCHEMA_SQL)
        self.conn.execute(NOTIFIED_SCHEMA_SQL)
        self.conn.commit()

    def upsert_calls(self, calls: Iterable[FundingCall]) -> None:
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

        self.conn.executemany(sql, rows)
        self.conn.commit()

    def get_top_calls(self, limit: int = 100) -> List[sqlite3.Row]:
        self.conn.row_factory = sqlite3.Row
        cur = self.conn.cursor()
        cur.execute(
            """
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
            LIMIT ?
            """,
            (limit,),
        )
        return cur.fetchall()

    def get_top_real_calls(self, limit: int = 100) -> List[sqlite3.Row]:
        self.conn.row_factory = sqlite3.Row
        cur = self.conn.cursor()
        cur.execute(
            """
            SELECT * FROM funding_calls
            WHERE record_type = 'call'
            ORDER BY relevance_score DESC, id DESC
            LIMIT ?
            """,
            (limit,),
        )
        return cur.fetchall()

    def get_all_real_calls(self) -> List[sqlite3.Row]:
        self.conn.row_factory = sqlite3.Row
        cur = self.conn.cursor()
        cur.execute(
            """
            SELECT * FROM funding_calls
            WHERE record_type = 'call'
            ORDER BY relevance_score DESC, id DESC
            """
        )
        return cur.fetchall()

    def get_unnotified_real_calls(self, min_score: float = 0.0) -> List[sqlite3.Row]:
        self.conn.row_factory = sqlite3.Row
        cur = self.conn.cursor()
        cur.execute(
            """
            SELECT fc.*
            FROM funding_calls fc
            LEFT JOIN notified_calls nc
              ON fc.source_url = nc.source_url
            WHERE fc.record_type = 'call'
              AND fc.relevance_score >= ?
              AND nc.source_url IS NULL
            ORDER BY fc.relevance_score DESC, fc.id DESC
            """,
            (min_score,),
        )
        return cur.fetchall()

    def mark_calls_notified(self, source_urls: List[str]) -> None:
        if not source_urls:
            return

        cur = self.conn.cursor()
        cur.executemany(
            """
            INSERT OR IGNORE INTO notified_calls (source_url)
            VALUES (?)
            """,
            [(url,) for url in source_urls],
        )
        self.conn.commit()

    def close(self) -> None:
        self.conn.close()