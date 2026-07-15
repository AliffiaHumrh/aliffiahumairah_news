"""
Backend Supabase (Postgres). Dipakai kalau DB_BACKEND=supabase (default).

Beda penting dengan sqlite_backend.py:
- Tabel HARUS dibuat lebih dulu lewat SQL Editor di dashboard Supabase,
  pakai schema.sql yang ada di root project ini. supabase-py (client
  library, bukan admin API) tidak bisa menjalankan CREATE TABLE.
  init_db() di sini hanya *mengecek* tabelnya sudah ada atau belum, dan
  kasih instruksi jelas kalau belum.
- Deduplikasi URL mengandalkan UNIQUE constraint di kolom `url` (sudah
  didefinisikan di schema.sql) + error code Postgres 23505 saat insert
  bentrok.
"""

import logging

import config

logger = logging.getLogger("news_crawler.db.supabase")

_client = None


def _get_client():
    global _client
    if _client is None:
        if not config.SUPABASE_URL or not config.SUPABASE_KEY:
            raise RuntimeError(
                "SUPABASE_URL / SUPABASE_KEY belum diset. Isi file .env "
                "(lihat .env.example) dengan kredensial project Supabase-mu, "
                "atau set DB_BACKEND=sqlite di .env kalau mau pakai SQLite dulu."
            )
        from supabase import create_client
        _client = create_client(config.SUPABASE_URL, config.SUPABASE_KEY)
    return _client


def init_db():
    """
    Tidak membuat tabel (client library tidak punya akses DDL) -- cuma
    verifikasi tabel `news` bisa diakses. Kalau belum ada, kasih instruksi.
    """
    client = _get_client()
    try:
        client.table("news").select("id").limit(1).execute()
        logger.info("Koneksi Supabase OK, tabel 'news' ditemukan.")
    except Exception as exc:
        raise RuntimeError(
            "Tabel 'news' belum ada / tidak bisa diakses di Supabase. "
            "Buka SQL Editor di dashboard Supabase-mu, jalankan isi "
            "schema.sql dari project ini, lalu coba lagi.\n"
            f"Detail error: {exc}"
        ) from exc


def url_exists(url: str) -> bool:
    client = _get_client()
    resp = client.table("news").select("id").eq("url", url).limit(1).execute()
    return len(resp.data) > 0


def insert_news(title: str, content: str, source: str, url: str, published_at: str | None) -> bool:
    client = _get_client()
    try:
        client.table("news").insert(
            {
                "title": title,
                "content": content,
                "source": source,
                "url": url,
                "published_at": published_at,
            }
        ).execute()
        return True
    except Exception as exc:
        # 23505 = unique_violation di Postgres -> url sudah ada, anggap duplikat
        if "23505" in str(exc) or "duplicate key" in str(exc).lower():
            return False
        logger.warning("Gagal insert ke Supabase: %s", exc)
        raise


def count_news() -> int:
    client = _get_client()
    resp = client.table("news").select("id", count="exact").limit(1).execute()
    return resp.count or 0


def count_by_source() -> list[dict]:
    """
    supabase-py (PostgREST) tidak punya GROUP BY langsung dari client.
    Untuk volume data tahap awal ini cukup ambil kolom source lalu
    diagregasi di Python. Kalau datanya sudah besar (>~50rb baris),
    ganti ini dengan Postgres function (RPC) yang di-`GROUP BY` di
    database langsung -- lebih efisien.
    """
    client = _get_client()
    resp = client.table("news").select("source").execute()
    counts: dict[str, int] = {}
    for row in resp.data:
        counts[row["source"]] = counts.get(row["source"], 0) + 1
    return [
        {"source": src, "total": total}
        for src, total in sorted(counts.items(), key=lambda x: -x[1])
    ]


def fetch_news(limit: int = 50, source: str | None = None, search: str | None = None) -> list[dict]:
    client = _get_client()
    query = client.table("news").select(
        "id, title, content, processed_content, source, url, published_at, created_at"
    )
    if source:
        query = query.eq("source", source)
    if search:
        query = query.ilike("title", f"%{search}%")

    resp = query.order("published_at", desc=True).limit(limit).execute()
    return resp.data


def list_sources() -> list[str]:
    client = _get_client()
    resp = client.table("news").select("source").execute()
    return sorted({row["source"] for row in resp.data})


def get_unprocessed_news(limit: int = 200) -> list[dict]:
    """
    Ambil berita yang belum punya processed_content (FR-04). Dipakai oleh
    preprocess_all.py untuk batch processing.
    """
    client = _get_client()
    resp = (
        client.table("news")
        .select("id, title, content")
        .is_("processed_content", "null")
        .limit(limit)
        .execute()
    )
    return resp.data


def update_processed_content(news_id: int, processed_content: str) -> None:
    client = _get_client()
    client.table("news").update({"processed_content": processed_content}).eq("id", news_id).execute()