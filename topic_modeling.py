"""
Topic modeling (FR-05) pakai BERTopic.

Beda dengan crawler/preprocessing yang inkremental (proses yang baru
saja), topic modeling ini SELALU jalan ke SEMUA berita yang sudah
di-preprocess sekaligus (bukan cuma yang belum punya topic_id) --
BERTopic butuh melihat seluruh korpus dokumen bersamaan supaya bisa
menemukan cluster yang bermakna. Menjalankan ke subset kecil per batch
tidak akan menghasilkan topik yang stabil.

Konsekuensinya: script ini idealnya dijalankan berkala (misal harian),
bukan tiap 30 menit seperti crawling. topic_id bisa berubah tiap kali
di-run ulang (cluster baru terbentuk) -- ini normal untuk topic modeling
berbasis clustering, beda dengan ID yang permanen seperti primary key.

CATATAN PERFORMA: proses ini berat -- download model embedding (~470MB,
sekali saja lalu di-cache), lalu hitung embedding untuk SETIAP berita,
baru clustering (UMAP + HDBSCAN). Untuk ribuan berita, ini bisa makan
waktu beberapa menit sampai puluhan menit tergantung spesifikasi mesin.
Jalankan dulu secara lokal untuk tahu berapa lama sebelum dipertimbangkan
untuk diotomatisasi.

Jalankan: python topic_modeling.py
"""

import logging
import sys

from bertopic import BERTopic
from sentence_transformers import SentenceTransformer

import db

# Model embedding multibahasa -- mendukung Bahasa Indonesia meski bukan
# model khusus Indonesia (tidak ada model sentence-embedding Indonesia
# semapan model multibahasa ini). Ukuran sedang (~470MB), akurasi cukup
# baik untuk multibahasa termasuk Indonesia.
EMBEDDING_MODEL_NAME = "paraphrase-multilingual-MiniLM-L12-v2"

# Minimal berapa berita supaya dianggap satu topik -- kalau kurang dari
# ini, dianggap noise/outlier (topic_id = -1). Nilai lebih kecil = lebih
# banyak topik granular tapi berisiko topik "sampah" dengan 2-3 berita.
# Angka ini perlu di-tuning setelah lihat hasilnya -- 10 adalah titik
# awal yang wajar untuk korpus ribuan berita.
MIN_TOPIC_SIZE = 10


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

    logger.info("Mengambil semua berita yang sudah di-preprocess...")
    news_rows = db.get_all_processed_news()
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

    # Simpan topic_id + label (nama topik hasil auto-generate BERTopic,
    # contoh: "0_korupsi_kejagung_kasus_febrie") kembali ke tiap berita.
    label_by_topic_id = dict(zip(topic_info["Topic"], topic_info["Name"]))

    logger.info("Menyimpan hasil ke database...")
    for row, topic_id in zip(news_rows, topics):
        label = label_by_topic_id.get(topic_id, "Tidak terklasifikasi")
        db.update_topic(row["id"], int(topic_id), label)

    logger.info("=== Ringkasan topik yang ditemukan ===")
    for _, row in topic_info.iterrows():
        if row["Topic"] == -1:
            logger.info("  [outlier/tidak terklasifikasi]: %d berita", row["Count"])
        else:
            logger.info("  Topik %d (%s): %d berita", row["Topic"], row["Name"], row["Count"])

    logger.info("Selesai. Total %d berita diberi topic_id.", len(news_rows))


if __name__ == "__main__":
    main()