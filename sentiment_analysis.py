import logging
import sys
import time

from transformers import pipeline

import db

MODEL_NAME = "aliffiaaliffia/indobert_sentiment_news"
MAX_LENGTH = 512
BATCH_SIZE = 200

MAX_RUNTIME_SECONDS = 10 * 60


def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )


def main():
    setup_logging()
    logger = logging.getLogger("news_crawler.sentiment_analysis")

    db.init_db()

    logger.info("Memuat model '%s' (unduh sekali, lalu di-cache lokal)...", MODEL_NAME)
    classifier = pipeline(
        "sentiment-analysis",
        model=MODEL_NAME,
        tokenizer=MODEL_NAME,
        truncation=True,
        max_length=MAX_LENGTH,
    )

    start_time = time.monotonic()
    total_processed = 0
    batch_num = 0

    while True:
        elapsed = time.monotonic() - start_time
        if elapsed > MAX_RUNTIME_SECONDS:
            logger.info(
                "Batas waktu internal (%d menit) tercapai -- berhenti dengan rapi. "
                "Sisa backlog akan lanjut diproses di run berikutnya (tidak ada data hilang).",
                MAX_RUNTIME_SECONDS // 60,
            )
            break

        batch_num += 1
        rows = db.get_unsentimented_news(limit=BATCH_SIZE)
        if not rows:
            logger.info("Tidak ada lagi backlog -- semua berita sudah punya sentiment.")
            break

        logger.info("Batch #%d: menganalisis sentimen %d berita...", batch_num, len(rows))

        texts = [f"{row.get('title', '')}. {row.get('content', '')}" for row in rows]
        results = classifier(texts)

        for row, result in zip(rows, results):
            db.update_sentiment(row["id"], result["label"], float(result["score"]))

        for row, result in list(zip(rows, results))[:3]:
            preview = f"{row.get('title', '')}"[:60]
            logger.info("  contoh: \"%s...\" -> %s (%.3f)", preview, result["label"], result["score"])

        total_processed += len(rows)

    logger.info("Selesai untuk run ini. Total %d berita diproses.", total_processed)


if __name__ == "__main__":
    main()