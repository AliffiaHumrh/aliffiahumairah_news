"""
Entry point. Jalankan dengan: python main.py

Alur:
1. Cek koneksi database siap (tabel Supabase harus sudah dibuat lewat
   schema.sql, atau tabel SQLite dibuat otomatis kalau DB_BACKEND=sqlite).
2. Jalankan satu kali crawling langsung (supaya ada data begitu dinyalakan,
   tidak perlu nunggu interval pertama).
3. Nyalakan scheduler supaya crawling berikutnya berjalan otomatis sesuai
   CRAWL_INTERVAL_MINUTES di config.py.
"""

import logging
import sys

import config
import db
from crawler import crawl_all_sources
from scheduler import run_forever


def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(config.LOG_PATH, encoding="utf-8"),
        ],
    )


def main():
    setup_logging()
    logger = logging.getLogger("news_crawler.main")

    db.init_db()

    logger.info("Menjalankan crawling awal sebelum scheduler dimulai...")
    crawl_all_sources()
    logger.info("Total berita di database saat ini: %d", db.count_news())

    run_forever()


if __name__ == "__main__":
    main()