"""
Sentiment analysis (FR-06) pakai IndoBERT.

Beda dengan topic modeling (FR-05) yang harus lihat SELURUH korpus
sekaligus untuk clustering, sentiment analysis ini INKREMENTAL per
berita -- satu berita dinilai independen dari berita lain. Makanya
script ini pakai pola batch seperti preprocess_all.py (proses yang
belum, lalu berhenti), bukan pola topic_modeling.py (selalu proses
semua ulang).

Sengaja pakai title+content ASLI (bukan processed_content yang sudah
di-stem & dibuang stopword-nya) -- BERT itu model yang membaca konteks
kalimat utuh, stemming malah merusak struktur gramatikal yang penting
untuk memahami nada kalimat. Preprocessing berat ala Sastrawi lebih
cocok untuk BERTopic (bag-of-words style clustering), bukan untuk model
berbasis transformer seperti BERT.

Model: aliffiaaliffia/indobert_sentiment_news -- model IndoBERT hasil
fine-tuning ulang pakai 1000 data berita yang dilabeli manual (bukan lagi
SmSA yang domainnya ulasan produk). TERVALIDASI lewat evaluasi formal:
akurasi 72-76% pada data uji independen (dua kali diukur dari sumber
berbeda: test split internal Colab dan sampel independen terpisah,
hasilnya konsisten) -- jauh lebih baik dari model versi SmSA (~41%) atau
model publik mdhugol (~43%), terutama recall kelas negative yang naik
dari 0.00 jadi 0.87.
"""

import logging
import sys

from transformers import pipeline

import db

MODEL_NAME = "aliffiaaliffia/indobert_sentiment_news"

# Batas token BERT (termasuk IndoBERT) itu 512 -- teks lebih panjang
# otomatis dipotong (truncation=True). Untuk judul+isi berita, ini
# biasanya cukup menangkap inti berita di awal paragraf.
MAX_LENGTH = 512
BATCH_SIZE = 200


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

    total_processed = 0
    batch_num = 0

    while True:
        batch_num += 1
        rows = db.get_unsentimented_news(limit=BATCH_SIZE)
        if not rows:
            break

        logger.info("Batch #%d: menganalisis sentimen %d berita...", batch_num, len(rows))

        texts = [f"{row.get('title', '')}. {row.get('content', '')}" for row in rows]
        results = classifier(texts)

        for row, result in zip(rows, results):
            # result contoh: {'label': 'LABEL_0', 'score': 0.87} atau
            # {'label': 'positive', 'score': 0.87} -- tergantung
            # bagaimana model kamu disimpan (id2label config saat push
            # ke HuggingFace). Dicatat APA ADANYA dari model, belum
            # tentu sudah berupa nama yang manusiawi. WAJIB dicek manual
            # setelah run pertama -- lihat print di akhir untuk contoh.
            db.update_sentiment(row["id"], result["label"], float(result["score"]))

        for row, result in zip(rows[:3], results[:3]):
            preview = f"{row.get('title', '')}"[:60]
            logger.info("  contoh: \"%s...\" -> %s (%.3f)", preview, result["label"], result["score"])

        total_processed += len(rows)

    logger.info("Selesai. Total %d berita dianalisis sentimennya.", total_processed)
    logger.info(
        "PENTING: cek beberapa contoh di atas -- pastikan label yang keluar "
        "cocok dengan makna judul beritanya (berita positif dapat label apa, "
        "berita negatif dapat label apa). Kalau labelnya masih berbentuk "
        "'LABEL_0'/'LABEL_1'/'LABEL_2' (bukan nama yang jelas), perlu mapping "
        "manual -- konfirmasi ke saya urutan yang benar."
    )


if __name__ == "__main__":
    main()