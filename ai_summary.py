"""
AI Summary: ringkasan naratif otomatis PER TOPIK.

PENTING soal desain ini -- baca sebelum percaya hasilnya begitu saja:

Model yang dipakai (cahya/t5-base-indonesian-summarization-cased) itu
didesain untuk meringkas SATU artikel (artikel panjang -> ringkasan
pendek dari artikel yang sama), dilatih dari dataset berita asli
(id_liputan6) -- jadi domain-nya cocok (beda dengan kasus sentiment
yang dulu domain-nya salah).

TAPI FR-08 minta ringkasan PER TOPIK (gabungan BANYAK artikel jadi satu
narasi), bukan ringkasan 1 artikel. Ini beda arsitektur tugas dari yang
didesain modelnya. Cara kita akali: ambil beberapa judul artikel
representatif dari satu topik, gabungkan jadi "pseudo-artikel", baru
diringkas modelnya. Ini BUKAN pemakaian yang 100% sesuai desain asli
model -- kualitas hasilnya WAJIB dicek manual sebelum dipercaya, sama
seperti kita evaluasi sentiment analysis dulu. Jangan asumsikan bagus
tanpa dicek.

Kalau setelah dicek kualitasnya jelek/kaku, pertimbangkan model
alternatif atau pindah ke opsi API LLM berbayar (biayanya kemungkinan
kecil untuk teks pendek seperti ini).

Jalankan: python ai_summary.py
"""

import logging
import sys
from datetime import datetime, timedelta, timezone

from transformers import pipeline

import db

MODEL_NAME = "cahya/t5-base-indonesian-summarization-cased"
ARTICLES_PER_TOPIC = 8  # jumlah judul artikel yang digabung jadi input
MIN_ARTICLES_FOR_SUMMARY = 3  # topik dengan artikel terlalu sedikit di-skip


def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )


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

    logger.info("Memuat model '%s' (unduh sekali, lalu di-cache lokal)...", MODEL_NAME)
    summarizer = pipeline("summarization", model=MODEL_NAME, tokenizer=MODEL_NAME)

    batch_timestamp = now.isoformat()
    results = []

    for i, (topic_id, info) in enumerate(active_topics.items(), 1):
        articles = db.get_articles_for_topic(topic_id, limit=ARTICLES_PER_TOPIC)
        if not articles:
            continue

        # Gabungkan judul-judul jadi satu "pseudo-artikel" -- ini akal-
        # akalan (lihat catatan di atas), bukan pemakaian standar model.
        pseudo_article = ". ".join(a["title"] for a in articles)

        try:
            result = summarizer(
                pseudo_article,
                max_length=100,
                min_length=20,
                do_sample=False,
                truncation=True,
            )
            summary_text = result[0]["summary_text"]
        except Exception as exc:
            logger.warning("Gagal generate summary untuk topik %s: %s", info["label"], exc)
            continue

        db.insert_topic_summary(
            topic_id=int(topic_id),
            topic_label=info["label"],
            summary_text=summary_text,
            article_count=info["count"],
            generated_at=batch_timestamp,
        )
        results.append((info["label"], info["count"], summary_text))

        if i % 10 == 0:
            logger.info("  ... %d/%d topik selesai diringkas", i, len(active_topics))

    logger.info("=== Contoh hasil (untuk dicek manual kualitasnya) ===")
    for label, count, summary in results[:5]:
        logger.info("  [%s] (%d artikel)", label, count)
        logger.info("    -> %s", summary)

    logger.info("Selesai. Total %d topik berhasil diringkas.", len(results))
    logger.info(
        "PENTING: baca ulang beberapa hasil di atas -- pastikan narasinya "
        "masuk akal dan bukan kalimat aneh/terpotong. Model ini dipakai "
        "di luar desain aslinya (lihat catatan di kepala file)."
    )


if __name__ == "__main__":
    main()