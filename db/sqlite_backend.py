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
    processed_content TEXT,
    topic_id INTEGER,
    topic_label TEXT,
    sentiment TEXT,
    sentiment_confidence REAL,
    source TEXT NOT NULL,
    url TEXT NOT NULL UNIQUE,
    published_at TEXT,
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_news_source ON news(source);
CREATE INDEX IF NOT EXISTS idx_news_published_at ON news(published_at);
CREATE INDEX IF NOT EXISTS idx_news_topic_id ON news(topic_id);

CREATE TABLE IF NOT EXISTS topic_trends (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    topic_id INTEGER NOT NULL,
    topic_label TEXT,
    news_count_recent INTEGER NOT NULL DEFAULT 0,
    news_count_previous INTEGER NOT NULL DEFAULT 0,
    growth_rate REAL,
    trend_score REAL,
    calculated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_topic_trends_calculated_at ON topic_trends(calculated_at);
CREATE INDEX IF NOT EXISTS idx_topic_trends_topic_id ON topic_trends(topic_id);

CREATE TABLE IF NOT EXISTS topic_summaries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    topic_id INTEGER NOT NULL,
    topic_label TEXT,
    summary_text TEXT,
    article_count INTEGER NOT NULL DEFAULT 0,
    generated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_topic_summaries_generated_at ON topic_summaries(generated_at);
CREATE INDEX IF NOT EXISTS idx_topic_summaries_topic_id ON topic_summaries(topic_id);
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
        # Migrasi ringan untuk database SQLite lama -- aman dipanggil berkali-kali.
        existing_cols = {row["name"] for row in conn.execute("PRAGMA table_info(news)")}
        if "processed_content" not in existing_cols:
            conn.execute("ALTER TABLE news ADD COLUMN processed_content TEXT")
        if "topic_id" not in existing_cols:
            conn.execute("ALTER TABLE news ADD COLUMN topic_id INTEGER")
        if "topic_label" not in existing_cols:
            conn.execute("ALTER TABLE news ADD COLUMN topic_label TEXT")
        if "sentiment" not in existing_cols:
            conn.execute("ALTER TABLE news ADD COLUMN sentiment TEXT")
        if "sentiment_confidence" not in existing_cols:
            conn.execute("ALTER TABLE news ADD COLUMN sentiment_confidence REAL")
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
    query = "SELECT id, title, content, processed_content, topic_id, topic_label, sentiment, sentiment_confidence, source, url, published_at, created_at FROM news"
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


def get_unprocessed_news(limit: int = 200) -> list[dict]:
    """
    Ambil berita yang belum punya processed_content (FR-04). Dipakai oleh
    preprocess_all.py untuk batch processing.
    """
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT id, title, content FROM news WHERE processed_content IS NULL LIMIT ?",
            (limit,),
        ).fetchall()
    return [dict(r) for r in rows]


def update_processed_content(news_id: int, processed_content: str) -> None:
    with get_connection() as conn:
        conn.execute(
            "UPDATE news SET processed_content = ? WHERE id = ?",
            (processed_content, news_id),
        )


def get_all_processed_news(limit: int = 10000) -> list[dict]:
    """
    Ambil semua berita yang sudah punya processed_content (FR-05: input
    untuk topic modeling). Beda dengan get_unprocessed_news() -- ini
    ambil yang SUDAH diproses, bukan yang belum.
    """
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT id, title, processed_content FROM news
            WHERE processed_content IS NOT NULL AND processed_content != ''
            ORDER BY id
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    return [dict(r) for r in rows]


def get_recent_processed_news(since_iso: str, limit: int = 20000) -> list[dict]:
    """
    Sama seperti get_all_processed_news(), tapi dibatasi ke berita yang
    created_at >= since_iso saja. Dipakai topic_modeling.py supaya waktu
    proses TIDAK terus membengkak seiring korpus total terus bertambah
    (crawler jalan 24/7 selamanya) -- tanpa batas waktu ini, topic
    modeling pasti kena timeout cepat atau lambat karena selalu proses
    SEMUA data sejak awal crawling.
    """
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT id, title, processed_content FROM news
            WHERE processed_content IS NOT NULL AND processed_content != ''
              AND created_at >= ?
            ORDER BY id
            LIMIT ?
            """,
            (since_iso, limit),
        ).fetchall()
    return [dict(r) for r in rows]


def update_topic(news_id: int, topic_id: int, topic_label: str) -> None:
    with get_connection() as conn:
        conn.execute(
            "UPDATE news SET topic_id = ?, topic_label = ? WHERE id = ?",
            (topic_id, topic_label, news_id),
        )


def bulk_update_topics(updates: list[dict]) -> None:
    """
    Versi batch dari update_topic -- di SQLite tidak ada masalah koneksi
    HTTP putus seperti Supabase, tapi tetap dibuat konsisten API-nya
    (dan executemany tetap lebih cepat dari banyak execute() terpisah).
    """
    if not updates:
        return
    with get_connection() as conn:
        conn.executemany(
            "UPDATE news SET topic_id = ?, topic_label = ? WHERE id = ?",
            [(u["topic_id"], u["topic_label"], u["id"]) for u in updates],
        )


def get_unsentimented_news(limit: int = 200) -> list[dict]:
    """
    Ambil berita yang sudah di-preprocess tapi belum punya sentiment
    (FR-06). Beda dengan topic modeling, sentiment analysis ini
    inkremental per-berita -- tidak perlu lihat seluruh korpus sekaligus.
    """
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT id, title, content FROM news
            WHERE processed_content IS NOT NULL AND sentiment IS NULL
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    return [dict(r) for r in rows]


def update_sentiment(news_id: int, sentiment: str, confidence: float) -> None:
    with get_connection() as conn:
        conn.execute(
            "UPDATE news SET sentiment = ?, sentiment_confidence = ? WHERE id = ?",
            (sentiment, confidence, news_id),
        )


def get_news_by_ids(ids: list[int]) -> list[dict]:
    """Ambil title+content untuk daftar ID spesifik (dipakai export_eval_sample.py)."""
    if not ids:
        return []
    with get_connection() as conn:
        placeholders = ",".join("?" * len(ids))
        rows = conn.execute(
            f"SELECT id, title, content FROM news WHERE id IN ({placeholders})",
            ids,
        ).fetchall()
    return [dict(r) for r in rows]


def get_topic_news_counts(start_iso: str, end_iso: str) -> dict[int, dict]:
    """
    Hitung jumlah berita per topic_id dalam rentang waktu [start_iso, end_iso)
    berdasarkan created_at. Return {topic_id: {"count": N, "label": "..."}}.
    topic_id = -1 (outlier/tidak terklasifikasi) DIKECUALIKAN -- tidak
    bermakna dihitung growth rate-nya karena isinya campur macam-macam topik.
    """
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT topic_id, topic_label, COUNT(*) as cnt
            FROM news
            WHERE topic_id IS NOT NULL AND topic_id != -1
              AND created_at >= ? AND created_at < ?
            GROUP BY topic_id
            """,
            (start_iso, end_iso),
        ).fetchall()
    return {r["topic_id"]: {"count": r["cnt"], "label": r["topic_label"]} for r in rows}


def insert_topic_trend(topic_id: int, topic_label: str, count_recent: int, count_previous: int, growth_rate: float, trend_score: float, calculated_at: str) -> None:
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO topic_trends
                (topic_id, topic_label, news_count_recent, news_count_previous, growth_rate, trend_score, calculated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (topic_id, topic_label, count_recent, count_previous, growth_rate, trend_score, calculated_at),
        )


def get_latest_trends(limit: int = 20) -> list[dict]:
    """Ambil snapshot trend terbaru, diurutkan dari trend_score tertinggi."""
    with get_connection() as conn:
        latest_time_row = conn.execute("SELECT MAX(calculated_at) as t FROM topic_trends").fetchone()
        if not latest_time_row or not latest_time_row["t"]:
            return []
        latest_time = latest_time_row["t"]
        rows = conn.execute(
            """
            SELECT * FROM topic_trends
            WHERE calculated_at = ?
            ORDER BY trend_score DESC
            LIMIT ?
            """,
            (latest_time, limit),
        ).fetchall()
    return [dict(r) for r in rows]


def get_articles_for_topic(topic_id: int, limit: int = 10) -> list[dict]:
    """Ambil beberapa artikel terbaru untuk satu topic_id (dipakai ai_summary.py)."""
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT id, title, content FROM news
            WHERE topic_id = ?
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (topic_id, limit),
        ).fetchall()
    return [dict(r) for r in rows]


def insert_topic_summary(topic_id: int, topic_label: str, summary_text: str, article_count: int, generated_at: str) -> None:
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO topic_summaries (topic_id, topic_label, summary_text, article_count, generated_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (topic_id, topic_label, summary_text, article_count, generated_at),
        )


def get_latest_summaries(limit: int = 20) -> list[dict]:
    """Ambil snapshot ringkasan topik terbaru."""
    with get_connection() as conn:
        latest_time_row = conn.execute("SELECT MAX(generated_at) as t FROM topic_summaries").fetchone()
        if not latest_time_row or not latest_time_row["t"]:
            return []
        latest_time = latest_time_row["t"]
        rows = conn.execute(
            """
            SELECT * FROM topic_summaries
            WHERE generated_at = ?
            ORDER BY article_count DESC
            LIMIT ?
            """,
            (latest_time, limit),
        ).fetchall()
    return [dict(r) for r in rows]