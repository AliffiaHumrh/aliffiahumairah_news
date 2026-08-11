import logging
import sys
from collections import Counter
from datetime import datetime, timedelta, timezone

import db

LOW_CONFIDENCE_THRESHOLD = 0.6


def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )


def main():
    setup_logging()
    logger = logging.getLogger("news_crawler.model_monitoring")

    db.init_db()

    now = datetime.now(timezone.utc)
    start = now - timedelta(hours=24)

    logger.info("Mengambil data sentiment 24 jam terakhir...")
    data = db.get_recent_sentiment_data(start.isoformat(), now.isoformat())

    if not data:
        logger.warning("Tidak ada data sentiment dalam 24 jam terakhir. Selesai tanpa hasil.")
        return

    total = len(data)
    confidences = [d["sentiment_confidence"] for d in data if d.get("sentiment_confidence") is not None]
    avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0
    low_conf_count = sum(1 for c in confidences if c < LOW_CONFIDENCE_THRESHOLD)
    pct_low_confidence = (low_conf_count / len(confidences) * 100) if confidences else 0.0

    label_counts = Counter(d["sentiment"] for d in data)

    db.insert_model_evaluation_log(
        log_type="daily_confidence",
        logged_at=now.isoformat(),
        total_analyzed=total,
        avg_confidence=avg_confidence,
        pct_low_confidence=pct_low_confidence,
        count_positive=label_counts.get("positive", 0),
        count_neutral=label_counts.get("neutral", 0),
        count_negative=label_counts.get("negative", 0),
        notes=f"Threshold confidence rendah: {LOW_CONFIDENCE_THRESHOLD}",
    )

    logger.info("=== Statistik confidence 24 jam terakhir ===")
    logger.info("  Total dianalisis: %d", total)
    logger.info("  Rata-rata confidence: %.3f", avg_confidence)
    logger.info("  Persentase confidence rendah (<%.1f): %.1f%%", LOW_CONFIDENCE_THRESHOLD, pct_low_confidence)
    logger.info("  Distribusi: positive=%d, neutral=%d, negative=%d",
                 label_counts.get("positive", 0), label_counts.get("neutral", 0), label_counts.get("negative", 0))
    logger.info("Selesai. Log tersimpan ke model_evaluation_log.")


if __name__ == "__main__":
    main()