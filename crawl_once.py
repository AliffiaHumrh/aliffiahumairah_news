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
  yang men-trigger script ini secara berkala.

Jalankan manual (untuk testing lokal): python crawl_once.py
"""

import logging
import os
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


def _select_sources() -> list[dict]:
    """
    Kalau dijalankan di GitHub Actions, otomatis skip sumber-sumber yang
    diketahui memblokir IP data center (lihat config.CI_BLOCKED_SOURCE_NAMES).
    Kalau dijalankan lokal (laptop), tetap crawl semua sumber seperti biasa.
    """
    if os.getenv("GITHUB_ACTIONS") == "true":
        skipped = [s for s in config.SOURCES if s["name"] in config.CI_BLOCKED_SOURCE_NAMES]
        selected = [s for s in config.SOURCES if s["name"] not in config.CI_BLOCKED_SOURCE_NAMES]
        if skipped:
            logging.getLogger("news_crawler.crawl_once").info(
                "Berjalan di GitHub Actions -- skip %d sumber yang diketahui "
                "memblokir IP data center: %s",
                len(skipped), ", ".join(s["name"] for s in skipped),
            )
        return selected
    return config.SOURCES


def main():
    setup_logging()
    logger = logging.getLogger("news_crawler.crawl_once")

    db.init_db()
    sources = _select_sources()
    crawl_all_sources(sources)

    # Ini cuma buat logging -- crawl & insert di atas sudah selesai dan
    # berhasil pada titik ini. Jangan biarkan query count yang gagal
    # (mis. Supabase statement timeout di tabel besar) bikin seluruh job
    # GitHub Actions ditandai gagal, soalnya itu bikin step berikutnya
    # (text preprocessing, sentiment analysis) ikut di-skip padahal
    # berita barunya sudah tersimpan dengan benar.
    try:
        logger.info("Total berita di database sekarang: %d", db.count_news())
    except Exception as exc:
        logger.warning("Gagal mengambil total jumlah berita (non-fatal): %s", exc)


if __name__ == "__main__":
    main()