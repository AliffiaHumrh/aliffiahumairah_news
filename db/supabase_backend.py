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
        "id, title, content, processed_content, topic_id, topic_label, sentiment, sentiment_confidence, source, url, published_at, created_at"
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


def get_all_processed_news(limit: int = 10000) -> list[dict]:
    """
    Ambil semua berita yang sudah punya processed_content (FR-05: input
    untuk topic modeling). Pakai pagination karena Supabase membatasi
    1000 baris per request (lihat pelajaran dari cleanup_html.py).
    """
    client = _get_client()
    rows: list[dict] = []
    page_size = 1000
    offset = 0
    while len(rows) < limit:
        resp = (
            client.table("news")
            .select("id, title, processed_content")
            .not_.is_("processed_content", "null")
            .neq("processed_content", "")
            .order("id")
            .range(offset, offset + page_size - 1)
            .execute()
        )
        batch = resp.data
        rows.extend(batch)
        if len(batch) < page_size:
            break
        offset += page_size
    return rows[:limit]


def get_recent_processed_news(since_iso: str, limit: int = 20000) -> list[dict]:
    """
    Sama seperti get_all_processed_news(), tapi dibatasi ke berita yang
    created_at >= since_iso saja. Dipakai topic_modeling.py supaya waktu
    proses TIDAK terus membengkak seiring korpus total terus bertambah
    (crawler jalan 24/7 selamanya) -- tanpa batas waktu ini, topic
    modeling pasti kena timeout cepat atau lambat karena selalu proses
    SEMUA data sejak awal crawling.
    """
    client = _get_client()
    rows: list[dict] = []
    page_size = 1000
    offset = 0
    while len(rows) < limit:
        resp = (
            client.table("news")
            .select("id, title, processed_content")
            .not_.is_("processed_content", "null")
            .neq("processed_content", "")
            .gte("created_at", since_iso)
            .order("id")
            .range(offset, offset + page_size - 1)
            .execute()
        )
        batch = resp.data
        rows.extend(batch)
        if len(batch) < page_size:
            break
        offset += page_size
    return rows[:limit]


def update_topic(news_id: int, topic_id: int, topic_label: str) -> None:
    client = _get_client()
    client.table("news").update({"topic_id": topic_id, "topic_label": topic_label}).eq("id", news_id).execute()


def bulk_update_topics(updates: list[dict]) -> None:
    """
    Update topic_id/topic_label untuk BANYAK berita sekaligus, dikirim
    dalam batch (bukan satu HTTP request per baris). Dipakai topic_modeling.py
    yang bisa memproses ribuan berita sekaligus -- kirim satu-satu terbukti
    bikin koneksi HTTP putus di tengah jalan (httpx.RemoteProtocolError)
    setelah puluhan ribu request berurutan dalam satu run yang lama.

    Pakai RPC (Postgres function bulk_update_topics, lihat schema.sql),
    BUKAN .upsert() -- upsert butuh semua kolom NOT NULL (title, content,
    source, url) ada di payload, padahal kita cuma mau UPDATE 2 kolom.
    RPC ini murni jalankan UPDATE, tidak menyentuh kolom lain sama sekali.

    updates: list of {"id": int, "topic_id": int, "topic_label": str}
    """
    if not updates:
        return
    client = _get_client()
    chunk_size = 500
    for i in range(0, len(updates), chunk_size):
        chunk = updates[i : i + chunk_size]
        client.rpc("bulk_update_topics", {"payload": chunk}).execute()


def get_unsentimented_news(limit: int = 200) -> list[dict]:
    """
    Ambil berita yang sudah di-preprocess tapi belum punya sentiment
    (FR-06). Beda dengan topic modeling, sentiment analysis ini
    inkremental per-berita -- tidak perlu lihat seluruh korpus sekaligus.
    """
    client = _get_client()
    resp = (
        client.table("news")
        .select("id, title, content")
        .not_.is_("processed_content", "null")
        .is_("sentiment", "null")
        .limit(limit)
        .execute()
    )
    return resp.data


def update_sentiment(news_id: int, sentiment: str, confidence: float) -> None:
    client = _get_client()
    client.table("news").update({"sentiment": sentiment, "sentiment_confidence": confidence}).eq("id", news_id).execute()


def get_news_by_ids(ids: list[int]) -> list[dict]:
    """
    Ambil title+content untuk daftar ID spesifik (dipakai export_eval_sample.py).
    Pakai .in_() filter -- AMAN dari batasan 1000 baris Supabase karena
    hasilnya difilter dulu berdasarkan ID (bukan mengambil dari awal
    tabel), jadi jumlah baris yang kembali otomatis sama dengan jumlah ID
    yang diminta, bukan dibatasi urutan.
    """
    if not ids:
        return []
    client = _get_client()
    resp = client.table("news").select("id, title, content").in_("id", ids).execute()
    return resp.data


def get_topic_news_counts(start_iso: str, end_iso: str) -> dict[int, dict]:
    """
    Hitung jumlah berita per topic_id dalam rentang waktu [start_iso, end_iso)
    berdasarkan created_at. Return {topic_id: {"count": N, "label": "..."}}.
    topic_id = -1 (outlier) dikecualikan. Pakai pagination karena bisa
    lebih dari 1000 baris.
    """
    client = _get_client()
    rows: list[dict] = []
    offset = 0
    page_size = 1000
    while True:
        resp = (
            client.table("news")
            .select("topic_id, topic_label")
            .not_.is_("topic_id", "null")
            .neq("topic_id", -1)
            .gte("created_at", start_iso)
            .lt("created_at", end_iso)
            .range(offset, offset + page_size - 1)
            .execute()
        )
        batch = resp.data
        rows.extend(batch)
        if len(batch) < page_size:
            break
        offset += page_size

    counts: dict[int, dict] = {}
    for row in rows:
        tid = row["topic_id"]
        if tid not in counts:
            counts[tid] = {"count": 0, "label": row.get("topic_label")}
        counts[tid]["count"] += 1
    return counts


def insert_topic_trend(topic_id: int, topic_label: str, count_recent: int, count_previous: int, growth_rate: float, trend_score: float, calculated_at: str) -> None:
    client = _get_client()
    client.table("topic_trends").insert(
        {
            "topic_id": topic_id,
            "topic_label": topic_label,
            "news_count_recent": count_recent,
            "news_count_previous": count_previous,
            "growth_rate": growth_rate,
            "trend_score": trend_score,
            "calculated_at": calculated_at,
        }
    ).execute()


def get_latest_trends(limit: int = 20) -> list[dict]:
    """Ambil snapshot trend terbaru, diurutkan dari trend_score tertinggi."""
    client = _get_client()
    latest_resp = client.table("topic_trends").select("calculated_at").order("calculated_at", desc=True).limit(1).execute()
    if not latest_resp.data:
        return []
    latest_time = latest_resp.data[0]["calculated_at"]
    resp = (
        client.table("topic_trends")
        .select("*")
        .eq("calculated_at", latest_time)
        .order("trend_score", desc=True)
        .limit(limit)
        .execute()
    )
    return resp.data


def get_articles_for_topic(topic_id: int, limit: int = 10) -> list[dict]:
    """Ambil beberapa artikel terbaru untuk satu topic_id (dipakai ai_summary.py)."""
    client = _get_client()
    resp = (
        client.table("news")
        .select("id, title, content")
        .eq("topic_id", topic_id)
        .order("created_at", desc=True)
        .limit(limit)
        .execute()
    )
    return resp.data


def insert_topic_summary(topic_id: int, topic_label: str, summary_text: str, article_count: int, generated_at: str) -> None:
    client = _get_client()
    client.table("topic_summaries").insert(
        {
            "topic_id": topic_id,
            "topic_label": topic_label,
            "summary_text": summary_text,
            "article_count": article_count,
            "generated_at": generated_at,
        }
    ).execute()


def get_latest_summaries(limit: int = 20) -> list[dict]:
    """Ambil snapshot ringkasan topik terbaru."""
    client = _get_client()
    latest_resp = client.table("topic_summaries").select("generated_at").order("generated_at", desc=True).limit(1).execute()
    if not latest_resp.data:
        return []
    latest_time = latest_resp.data[0]["generated_at"]
    resp = (
        client.table("topic_summaries")
        .select("*")
        .eq("generated_at", latest_time)
        .order("article_count", desc=True)
        .limit(limit)
        .execute()
    )
    return resp.data