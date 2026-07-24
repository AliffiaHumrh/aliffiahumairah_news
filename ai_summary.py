import logging
import sys
from datetime import datetime, timedelta, timezone

import numpy as np
from sentence_transformers import SentenceTransformer

import db

EMBEDDING_MODEL_NAME = "paraphrase-multilingual-MiniLM-L12-v2"
ARTICLES_TO_FETCH = 20       # ambil sampai 20 artikel terbaru per topik
REPRESENTATIVE_COUNT = 4     # pilih 4 judul paling representatif dari situ
MIN_ARTICLES_FOR_SUMMARY = 3


def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )


def select_representative_titles(model: SentenceTransformer, titles: list[str], count: int) -> list[str]:
    """
    Pilih N judul yang paling "mewakili" keseluruhan topik -- diukur dari
    kedekatan (cosine similarity) ke centroid (rata-rata) embedding semua
    judul di topik itu. Judul yang paling dekat ke centroid dianggap
    paling representatif dari "inti" topik tersebut.
    """
    if len(titles) <= count:
        return titles

    embeddings = model.encode(titles)
    centroid = np.mean(embeddings, axis=0)

    norms = np.linalg.norm(embeddings, axis=1) * np.linalg.norm(centroid) + 1e-8
    similarities = (embeddings @ centroid) / norms

    top_indices = np.argsort(-similarities)[:count]
    top_indices_sorted = sorted(top_indices)
    return [titles[i] for i in top_indices_sorted]


def build_extractive_summary(article_count: int, representative_titles: list[str]) -> str:
    bullet_list = "\n".join(f"- {t}" for t in representative_titles)
    return f"Topik ini mencakup {article_count} berita. Beberapa di antaranya:\n{bullet_list}"


def main():
    setup_logging()
    logger = logging.getLogger("news_crawler.ai_summary")

    db.init_db()

    now = datetime.now(timezone.utc)
    start = now - timedelta(hours=24)

    logger.info("Mencari topik yang aktif dalam 24 jam terakhir...")
    recent_counts = db.get_topic_news_counts(start.isoformat(), now.isoformat())
    active_topics = {
        tid: info for tid, info in recent_counts.items()
        if info["count"] >= MIN_ARTICLES_FOR_SUMMARY
    }
    logger.info("Total %d topik aktif (>= %d artikel dalam 24 jam terakhir).", len(active_topics), MIN_ARTICLES_FOR_SUMMARY)

    if not active_topics:
        logger.warning("Tidak ada topik yang cukup aktif untuk diringkas. Selesai tanpa hasil.")
        return

    logger.info("Memuat model embedding '%s' (dipakai juga oleh topic_modeling.py)...", EMBEDDING_MODEL_NAME)
    model = SentenceTransformer(EMBEDDING_MODEL_NAME)

    batch_timestamp = now.isoformat()
    results = []

    for i, (topic_id, info) in enumerate(active_topics.items(), 1):
        articles = db.get_articles_for_topic(topic_id, limit=ARTICLES_TO_FETCH)
        if not articles:
            continue

        titles = [a["title"] for a in articles]
        representative = select_representative_titles(model, titles, REPRESENTATIVE_COUNT)
        summary_text = build_extractive_summary(info["count"], representative)

        db.insert_topic_summary(
            topic_id=int(topic_id),
            topic_label=info["label"],
            summary_text=summary_text,
            article_count=info["count"],
            generated_at=batch_timestamp,
        )
        results.append((info["label"], info["count"], summary_text))

        if i % 20 == 0:
            logger.info("  ... %d/%d topik selesai diringkas", i, len(active_topics))

    logger.info("=== Contoh hasil ===")
    for label, count, summary in results[:5]:
        logger.info("  [%s] (%d artikel)", label, count)
        for line in summary.split("\n"):
            logger.info("    %s", line)

    logger.info("Selesai. Total %d topik berhasil diringkas.", len(results))


if __name__ == "__main__":
    main()