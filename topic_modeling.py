"""
Topic modeling (FR-05) pakai BERTopic.

Beda dengan crawler/preprocessing yang inkremental (proses yang baru
saja), topic modeling ini SELALU jalan ke SEMUA berita DALAM JENDELA
WAKTU TERTENTU sekaligus (bukan cuma yang belum punya topic_id) --
BERTopic butuh melihat seluruh korpus dokumen bersamaan supaya bisa
menemukan cluster yang bermakna. Menjalankan ke subset kecil per batch
tidak akan menghasilkan topik yang stabil.

Dibatasi ke TOPIC_MODELING_WINDOW_DAYS terakhir, bukan
SELURUH riwayat sejak awal crawling: karena crawler jalan 24/7 selamanya,
volume data terus bertambah setiap hari. Kalau topic modeling selalu
proses SEMUA data sejak awal, waktu prosesnya juga terus membengkak
setiap hari -- cepat atau lambat PASTI kena timeout di GitHub Actions
(ini sudah kejadian nyata: run pertama 17 Juli sukses ~29 menit, tapi
run-run berikutnya konsisten timeout di ~30 menit karena volume data
terus bertambah). Membatasi ke jendela waktu tetap (misal 30 hari
terakhir) membuat waktu proses stabil konstan dari waktu ke waktu,
berapa lama pun crawler sudah berjalan total.

Konsekuensinya: berita yang lebih lama dari jendela waktu ini topic_id-
nya TIDAK diperbarui lagi (tetap dengan topic_id dari run terakhir waktu
mereka masih dalam jendela). Ini trade-off yang wajar -- topik dari
berita berbulan-bulan lalu memang tidak relevan lagi untuk "trending
topics" hari ini.

Dijadwalkan berkala (misal harian), bukan tiap 30 menit seperti crawling.
"""

import logging
import sys
from datetime import datetime, timedelta, timezone

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

# Jendela waktu yang diproses -- lihat penjelasan panjang di docstring
# atas soal kenapa ini krusial untuk cegah timeout berulang. 30 hari
# dipilih sebagai titik awal yang wajar untuk "trending topics"; bisa
# diperkecil (misal 14 hari) kalau volume harian sangat besar dan tetap
# kena timeout, atau diperbesar kalau volumenya kecil dan masih ada sisa
# waktu jauh dari batas timeout.
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

    # Simpan topic_id + label (nama topik hasil auto-generate BERTopic,
    # contoh: "0_korupsi_kejagung_kasus_febrie") kembali ke tiap berita.
    label_by_topic_id = dict(zip(topic_info["Topic"], topic_info["Name"]))

    # Kumpulkan dulu semua hasil, baru simpan sekaligus lewat batch update
    # -- update satu-satu per baris (ribuan HTTP request berurutan)
    # terbukti bikin koneksi ke Supabase putus di tengah proses untuk
    # data sebanyak ini.
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