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
        if "23505" in str(exc) or "duplicate key" in str(exc).lower():
            return False
        logger.warning("Gagal insert ke Supabase: %s", exc)
        raise


def count_news() -> int:
    client = _get_client()
    resp = client.table("news").select("id", count="exact").limit(1).execute()
    return resp.count or 0


def count_by_source() -> list[dict]:
    
    client = _get_client()
    counts: dict[str, int] = {}
    offset = 0
    page_size = 1000
    while True:
        resp = client.table("news").select("source").range(offset, offset + page_size - 1).execute()
        batch = resp.data
        for row in batch:
            counts[row["source"]] = counts.get(row["source"], 0) + 1
        if len(batch) < page_size:
            break
        offset += page_size
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
    all_sources: set[str] = set()
    offset = 0
    page_size = 1000
    while True:
        resp = client.table("news").select("source").range(offset, offset + page_size - 1).execute()
        batch = resp.data
        all_sources.update(row["source"] for row in batch)
        if len(batch) < page_size:
            break
        offset += page_size
    return sorted(all_sources)


def get_unprocessed_news(limit: int = 200) -> list[dict]:
    
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


def get_all_processed_news(limit: int = 200000) -> list[dict]:

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


def get_recent_processed_news(since_iso: str, limit: int = 50000) -> list[dict]:
    
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
            .order("id", desc=True)
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
    if not updates:
        return
    client = _get_client()
    chunk_size = 500
    for i in range(0, len(updates), chunk_size):
        chunk = updates[i : i + chunk_size]
        client.rpc("bulk_update_topics", {"payload": chunk}).execute()


def get_unsentimented_news(limit: int = 200) -> list[dict]:

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

    if not ids:
        return []
    client = _get_client()
    resp = client.table("news").select("id, title, content").in_("id", ids).execute()
    return resp.data


def get_topic_news_counts(start_iso: str, end_iso: str) -> dict[int, dict]:

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
    """Ambil beberapa artikel terbaru untuk satu topic_id (dipakai ai_summary.py, recommendation_engine.py)."""
    client = _get_client()
    resp = (
        client.table("news")
        .select("id, title, content, sentiment, url")
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


def insert_recommendation(topic_id: int, topic_label: str, recommendation_score: float, dominant_sentiment: str, reason: str, generated_at: str) -> None:
    client = _get_client()
    client.table("recommendations").insert(
        {
            "topic_id": topic_id,
            "topic_label": topic_label,
            "recommendation_score": recommendation_score,
            "dominant_sentiment": dominant_sentiment,
            "reason": reason,
            "generated_at": generated_at,
        }
    ).execute()


def get_latest_recommendations(limit: int = 20) -> list[dict]:
    client = _get_client()
    latest_resp = client.table("recommendations").select("generated_at").order("generated_at", desc=True).limit(1).execute()
    if not latest_resp.data:
        return []
    latest_time = latest_resp.data[0]["generated_at"]
    resp = (
        client.table("recommendations")
        .select("*")
        .eq("generated_at", latest_time)
        .order("recommendation_score", desc=True)
        .limit(limit)
        .execute()
    )
    return resp.data

def update_recommendation_status(recommendation_id: int, status: str) -> None:
    client = _get_client()
    client.table("recommendations").update({"status": status}).eq("id", recommendation_id).execute()