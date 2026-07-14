"""
Entry point khusus untuk dijalankan oleh scheduler EKSTERNAL (GitHub
Actions), bukan oleh scheduler internal Python.

Beda dengan main.py:
- main.py menyalakan APScheduler (BlockingScheduler) yang menahan proses
  tetap hidup selamanya dan crawl ulang tiap N menit dari DALAM proses
  itu sendiri. Cocok untuk dijalankan manual di laptop/server yang
  memang mau dibiarkan nyala terus.
- crawl_once.py TIDAK menyalakan scheduler apa pun -- dia cuma crawl
  SEKALI lalu keluar (exit). Penjadwalan "ulang tiap 30 menit" diambil
  alih sepenuhnya oleh GitHub Actions (lihat .github/workflows/crawl.yml)
  yang men-trigger script ini secara berkala. Ini didesain untuk
  dijalankan di container baru setiap kali dipanggil, bukan proses lama
  yang idle menunggu.

Jalankan manual (untuk testing lokal): python crawl_once.py
"""

import logging
import sys

import config
import db
from crawler import crawl_all_sources


def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )


def main():
    setup_logging()
    logger = logging.getLogger("news_crawler.crawl_once")

    db.init_db()
    crawl_all_sources()
    logger.info("Total berita di database sekarang: %d", db.count_news())


if __name__ == "__main__":
    main()