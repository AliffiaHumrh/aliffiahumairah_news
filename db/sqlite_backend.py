"""
Backend SQLite. Dipakai kalau DB_BACKEND=sqlite. Nol setup, cocok untuk
development lokal atau kalau belum ada project Supabase.

Semua fungsi publik di sini punya signature yang sama persis dengan
supabase_backend.py -- lihat db/__init__.py untuk facade-nya.
"""

import logging
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone

import config

logger = logging.getLogger("news_crawler.db.sqlite")

SCHEMA = """
CREATE TABLE IF NOT EXISTS news (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    content TEXT,
    source TEXT NOT NULL,
    url TEXT NOT NULL UNIQUE,
    published_at TEXT,
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_news_source ON news(source);
CREATE INDEX IF NOT EXISTS idx_news_published_at ON news(published_at);
"""


@contextmanager
def get_connection():
    conn = sqlite3.connect(config.DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    with get_connection() as conn:
        conn.executescript(SCHEMA)
    logger.info("Database SQLite siap di %s", config.DB_PATH)


def url_exists(url: str) -> bool:
    with get_connection() as conn:
        row = conn.execute("SELECT 1 FROM news WHERE url = ? LIMIT 1", (url,)).fetchone()
    return row is not None


def insert_news(title: str, content: str, source: str, url: str, published_at: str | None) -> bool:
    try:
        with get_connection() as conn:
            conn.execute(
                """
                INSERT INTO news (title, content, source, url, published_at, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (title, content, source, url, published_at, datetime.now(timezone.utc).isoformat()),
            )
        return True
    except sqlite3.IntegrityError:
        return False


def count_news() -> int:
    with get_connection() as conn:
        row = conn.execute("SELECT COUNT(*) AS c FROM news").fetchone()
    return row["c"]


def count_by_source() -> list[dict]:
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT source, COUNT(*) AS total FROM news GROUP BY source ORDER BY total DESC"
        ).fetchall()
    return [dict(r) for r in rows]


def fetch_news(limit: int = 50, source: str | None = None, search: str | None = None) -> list[dict]:
    """Dipakai oleh dashboard Streamlit untuk menampilkan berita terbaru."""
    query = "SELECT id, title, content, source, url, published_at, created_at FROM news"
    conditions, params = [], []

    if source:
        conditions.append("source = ?")
        params.append(source)
    if search:
        conditions.append("title LIKE ?")
        params.append(f"%{search}%")
    if conditions:
        query += " WHERE " + " AND ".join(conditions)

    query += " ORDER BY published_at DESC LIMIT ?"
    params.append(limit)

    with get_connection() as conn:
        rows = conn.execute(query, params).fetchall()
    return [dict(r) for r in rows]


def list_sources() -> list[str]:
    with get_connection() as conn:
        rows = conn.execute("SELECT DISTINCT source FROM news ORDER BY source").fetchall()
    return [r["source"] for r in rows]
