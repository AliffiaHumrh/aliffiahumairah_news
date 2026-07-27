import logging
import sys
from collections import Counter
from datetime import datetime, timezone

import db

MIN_RECOMMENDATION_SCORE_TOPICS = 1  # minimal 1 topik dengan growth positif untuk lanjut


def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )


def get_sentiment_summary(topic_id: int) -> tuple[str, dict]:
    """
    Ambil distribusi sentimen dari artikel-artikel topik ini. Return
    (label_sentimen_dominan, {"positive": N, "neutral": N, "negative": N}).
    """
    articles = db.get_articles_for_topic(topic_id, limit=50)
    sentiments = [a["sentiment"] for a in articles if a.get("sentiment")]
    if not sentiments:
        return "tidak diketahui", {}

    counts = Counter(sentiments)
    dominant = counts.most_common(1)[0][0]
    return dominant, dict(counts)


def build_reason(topic_label: str, count_recent: int, growth_rate: float, dominant_sentiment: str, sentiment_counts: dict) -> str:
    growth_pct = growth_rate * 100
    total_sentimented = sum(sentiment_counts.values())

    reason = (
        f"Topik ini mengalami kenaikan volume berita sebesar {growth_pct:.0f}% "
        f"dalam 24 jam terakhir, dengan {count_recent} berita -- menjadikannya "
        f"salah satu topik paling aktif saat ini."
    )

    if total_sentimented > 0:
        dominant_pct = (sentiment_counts.get(dominant_sentiment, 0) / total_sentimented) * 100
        reason += (
            f" Sentimen pemberitaan sejauh ini didominasi {dominant_sentiment} "
            f"({dominant_pct:.0f}% dari {total_sentimented} berita yang dianalisis)."
        )
        if dominant_sentiment == "negative":
            reason += " Perhatikan konteks sensitif topik ini saat memutuskan sudut liputan."

    return reason


def main():
    setup_logging()
    logger = logging.getLogger("news_crawler.recommendation_engine")

    db.init_db()

    logger.info("Mengambil snapshot trend terbaru...")
    trends = db.get_latest_trends(limit=1000)

    # Hanya topik yang lagi NAIK (growth_rate > 0) yang layak direkomendasikan
    rising_topics = [t for t in trends if (t.get("growth_rate") or 0) > 0]
    logger.info(
        "Total %d topik di snapshot trend, %d di antaranya sedang naik (growth_rate > 0).",
        len(trends), len(rising_topics),
    )

    if len(rising_topics) < MIN_RECOMMENDATION_SCORE_TOPICS:
        logger.warning("Tidak cukup topik yang sedang naik untuk direkomendasikan. Selesai tanpa hasil.")
        return

    max_trend_score = max(t["trend_score"] for t in rising_topics)
    if max_trend_score <= 0:
        logger.warning("max_trend_score <= 0, tidak bisa normalisasi. Selesai tanpa hasil.")
        return

    now = datetime.now(timezone.utc)
    batch_timestamp = now.isoformat()
    results = []

    for t in rising_topics:
        topic_id = t["topic_id"]
        topic_label = t["topic_label"]
        trend_score = t["trend_score"]
        growth_rate = t["growth_rate"]
        count_recent = t["news_count_recent"]

        recommendation_score = min(100.0, (trend_score / max_trend_score) * 100)

        dominant_sentiment, sentiment_counts = get_sentiment_summary(topic_id)
        reason = build_reason(topic_label, count_recent, growth_rate, dominant_sentiment, sentiment_counts)

        db.insert_recommendation(
            topic_id=int(topic_id),
            topic_label=topic_label,
            recommendation_score=recommendation_score,
            dominant_sentiment=dominant_sentiment,
            reason=reason,
            generated_at=batch_timestamp,
        )
        results.append((topic_label, recommendation_score, dominant_sentiment, reason))

    results.sort(key=lambda r: -r[1])

    logger.info("=== Top 10 rekomendasi ===")
    for label, score, sentiment, reason in results[:10]:
        logger.info("  [%s] skor=%.1f, sentimen dominan=%s", label, score, sentiment)
        logger.info("    alasan: %s", reason)

    logger.info("Selesai. Total %d rekomendasi disimpan.", len(results))


if __name__ == "__main__":
    main()