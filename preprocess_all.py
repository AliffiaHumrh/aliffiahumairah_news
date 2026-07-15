"""
Batch text preprocessing (FR-04).

Ambil berita yang belum punya processed_content, jalankan pipeline
preprocessing.preprocess() (cleaning, case folding, stopword removal,
stemming), simpan hasilnya balik ke kolom processed_content.

Idempotent -- baris yang sudah punya processed_content otomatis dilewati
(lihat db.get_unprocessed_news()), jadi aman dijalankan berkali-kali atau
dijadwalkan rutin setelah crawling.

Jalankan: python preprocess_all.py
"""

import logging
import sys

import db
from preprocessing import preprocess


def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )


def main():
    setup_logging()
    logger = logging.getLogger("news_crawler.preprocess_all")

    db.init_db()
    processed_count = 0
    batch_num = 0

    while True:
        batch_num += 1
        batch = db.get_unprocessed_news(limit=200)
        if not batch:
            break

        logger.info("Batch #%d: memproses %d berita...", batch_num, len(batch))
        for row in batch:
            # Gabungkan title + content supaya konteks lebih kaya untuk
            # topic modeling nanti -- judul sering memuat kata kunci utama.
            raw_text = f"{row.get('title', '')} {row.get('content', '')}"
            result = preprocess(raw_text)
            db.update_processed_content(row["id"], result["stemmed"])
            processed_count += 1

    logger.info("Selesai. Total %d berita diproses.", processed_count)


if __name__ == "__main__":
    main()