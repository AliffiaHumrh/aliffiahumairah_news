import html
import logging
import re
import time

import feedparser

import config
import db

logger = logging.getLogger("news_crawler.crawler")

_TAG_RE = re.compile(r"<[^>]+>")


def clean_html(raw: str) -> str:
    """
    Beberapa sumber RSS (CNN Indonesia, Kompas, dll) menaruh HTML mentah
    di field description/summary mereka -- termasuk tag <img>. Fungsi ini
    membuang semua tag HTML dan decode entity (&amp; -> &, dst), supaya
    yang tersimpan di database murni teks bersih. Ini juga jadi langkah
    awal yang berguna untuk text preprocessing (FR-04) nanti.
    """
    if not raw:
        return raw
    text = _TAG_RE.sub(" ", raw)
    text = html.unescape(text)
    return re.sub(r"\s+", " ", text).strip()


def _parse_feed(source_name: str, url: str):
    """Ambil dan parse satu RSS feed. Return list of entries (bisa kosong)."""
    feedparser.USER_AGENT = config.USER_AGENT
    parsed = feedparser.parse(url)

    if parsed.bozo and not parsed.entries:
        raise ValueError(f"Gagal parse feed ({parsed.get('bozo_exception', 'unknown error')})")

    return parsed.entries


def _extract_published(entry) -> str | None:
    for field in ("published", "updated", "pubDate"):
        value = entry.get(field)
        if value:
            return value
    return None


def _extract_content(entry) -> str:
    if "summary" in entry:
        return clean_html(entry.summary)
    if "description" in entry:
        return clean_html(entry.description)
    return ""


def crawl_source(source: dict) -> dict:
    """
    Crawl satu sumber. Return ringkasan hasil untuk logging/observability:
    {"source": ..., "fetched": N, "new": N, "duplicate": N, "error": str|None}
    """
    name, url = source["name"], source["url"]
    result = {"source": name, "fetched": 0, "new": 0, "duplicate": 0, "error": None}

    try:
        entries = _parse_feed(name, url)
        result["fetched"] = len(entries)

        for entry in entries:
            article_url = entry.get("link")
            if not article_url:
                continue

            if db.url_exists(article_url):
                result["duplicate"] += 1
                continue

            saved = db.insert_news(
                title=entry.get("title", "(tanpa judul)"),
                content=_extract_content(entry),
                source=name,
                url=article_url,
                published_at=_extract_published(entry),
            )
            if saved:
                result["new"] += 1
            else:
                result["duplicate"] += 1

        logger.info(
            "[%s] fetched=%d new=%d duplicate=%d",
            name, result["fetched"], result["new"], result["duplicate"],
        )

    except Exception as exc:  # noqa: BLE001 -- sengaja luas: satu sumber gagal != pipeline gagal
        result["error"] = str(exc)
        logger.warning("[%s] GAGAL crawling: %s", name, exc)

    return result


def crawl_all_sources(sources: list[dict] | None = None) -> list[dict]:
    """
    Jalankan crawling untuk daftar sumber yang diberikan (default:
    config.SOURCES, yaitu semua sumber) secara berurutan, dengan jeda
    antar-sumber (rate limiting sesuai catatan PRD soal tidak membebani
    server sumber).
    """
    if sources is None:
        sources = config.SOURCES

    logger.info("=== Mulai crawling (%d sumber) ===", len(sources))
    results = []

    for i, source in enumerate(sources):
        results.append(crawl_source(source))
        if i < len(sources) - 1:
            time.sleep(config.DELAY_BETWEEN_SOURCES_SECONDS)

    total_new = sum(r["new"] for r in results)
    total_dup = sum(r["duplicate"] for r in results)
    total_err = sum(1 for r in results if r["error"])
    logger.info(
        "=== Selesai crawling: %d berita baru, %d duplikat, %d sumber gagal ===",
        total_new, total_dup, total_err,
    )
    return results