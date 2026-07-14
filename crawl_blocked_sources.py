"""
Entry point KHUSUS untuk sumber-sumber yang diketahui memblokir IP data
center (config.CI_BLOCKED_SOURCE_NAMES) -- CNN Indonesia, CNBC Indonesia,
Tempo.

Dipanggil oleh workflow GitHub Actions TERPISAH (crawl-blocked.yml) yang
jadwalnya jauh lebih jarang (1x sehari, bukan tiap 30 menit) -- ini
eksperimen: kadang situs yang mendeteksi "pola request terlalu sering &
teratur" lebih permisif kalau frekuensinya rendah. TIDAK ada jaminan ini
akan berhasil kalau blokirnya murni berdasarkan reputasi IP (bukan
rate-limiting) -- kalau setelah beberapa hari masih GAGAL terus,
workflow ini aman dihapus/dinonaktifkan tanpa mempengaruhi crawler utama.

Jalankan manual (testing lokal): python crawl_blocked_sources.py
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
    logger = logging.getLogger("news_crawler.crawl_blocked_sources")

    db.init_db()
    sources = [s for s in config.SOURCES if s["name"] in config.CI_BLOCKED_SOURCE_NAMES]

    if not sources:
        logger.warning(
            "Tidak ada sumber yang cocok dengan CI_BLOCKED_SOURCE_NAMES -- "
            "cek config.py, mungkin nama sumber sudah berubah."
        )
        return

    logger.info("Mencoba crawl %d sumber yang biasanya diblokir...", len(sources))
    crawl_all_sources(sources)
    logger.info("Total berita di database sekarang: %d", db.count_news())


if __name__ == "__main__":
    main()