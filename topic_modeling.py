import logging
import sys
from datetime import datetime, timedelta, timezone

from bertopic import BERTopic
from sentence_transformers import SentenceTransformer

import db

# Model embedding multibahasa
EMBEDDING_MODEL_NAME = "paraphrase-multilingual-MiniLM-L12-v2"


MIN_TOPIC_SIZE = 10


TOPIC_MODELING_WINDOW_DAYS = 30


def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )


def main():
    setup_logging()
    logger = logging.getLogger("news_crawler.topic_modeling")

    db.init_db()

    since = datetime.now(timezone.utc) - timedelta(days=TOPIC_MODELING_WINDOW_DAYS)
    logger.info(
        "Mengambil berita %d hari terakhir (sejak %s) yang sudah di-preprocess...",
        TOPIC_MODELING_WINDOW_DAYS, since.date(),
    )
    news_rows = db.get_recent_processed_news(since.isoformat())
    logger.info("Total %d berita akan di-topic-modeling.", len(news_rows))

    if len(news_rows) < MIN_TOPIC_SIZE * 2:
        logger.warning(
            "Data terlalu sedikit (%d berita) untuk topic modeling yang bermakna. "
            "Minimal disarankan %d+ berita. Jalankan crawler & preprocessing lebih "
            "lama dulu sebelum topic modeling.",
            len(news_rows), MIN_TOPIC_SIZE * 4,
        )
        return

    documents = [row["processed_content"] for row in news_rows]

    logger.info("Memuat model embedding '%s' (unduh sekali, lalu di-cache lokal)...", EMBEDDING_MODEL_NAME)
    embedding_model = SentenceTransformer(EMBEDDING_MODEL_NAME)

    logger.info("Menghitung embedding untuk %d dokumen...", len(documents))
    embeddings = embedding_model.encode(documents, show_progress_bar=True)

    logger.info("Menjalankan clustering BERTopic (min_topic_size=%d)...", MIN_TOPIC_SIZE)
    topic_model = BERTopic(
        embedding_model=embedding_model,
        min_topic_size=MIN_TOPIC_SIZE,
        language="multilingual",
        calculate_probabilities=False,
        verbose=True,
    )
    topics, _ = topic_model.fit_transform(documents, embeddings)

    topic_info = topic_model.get_topic_info()
    logger.info("Ditemukan %d topik (di luar outlier).", len(topic_info[topic_info["Topic"] != -1]))

    label_by_topic_id = dict(zip(topic_info["Topic"], topic_info["Name"]))


    logger.info("Menyimpan hasil ke database (batch update)...")
    updates = []
    for row, topic_id in zip(news_rows, topics):
        label = label_by_topic_id.get(topic_id, "Tidak terklasifikasi")
        updates.append({"id": row["id"], "topic_id": int(topic_id), "topic_label": label})

    db.bulk_update_topics(updates)

    logger.info("=== Ringkasan topik yang ditemukan ===")
    for _, row in topic_info.iterrows():
        if row["Topic"] == -1:
            logger.info("  [outlier/tidak terklasifikasi]: %d berita", row["Count"])
        else:
            logger.info("  Topik %d (%s): %d berita", row["Topic"], row["Name"], row["Count"])

    logger.info("Selesai. Total %d berita diberi topic_id.", len(news_rows))


if __name__ == "__main__":
    main()