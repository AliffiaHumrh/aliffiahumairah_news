"""
Scheduler (bagian "terjadwal" dari FR-01).

Pakai APScheduler sesuai tech stack di PRD. `run_forever()` dipakai kalau
crawler dijalankan sebagai proses berdiri sendiri (`python main.py`).
Nanti kalau dashboard Streamlit sudah ada, scheduler ini bisa dijalankan
di proses terpisah dari dashboard (disarankan) supaya restart dashboard
tidak mematikan jadwal crawling.
"""

import logging

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.interval import IntervalTrigger

import config
from crawler import crawl_all_sources

logger = logging.getLogger("news_crawler.scheduler")


def run_forever():
    scheduler = BlockingScheduler(timezone="Asia/Jakarta")
    scheduler.add_job(
        crawl_all_sources,
        trigger=IntervalTrigger(minutes=config.CRAWL_INTERVAL_MINUTES),
        id="crawl_news",
        name="Crawl semua sumber berita",
        next_run_time=None,  # run pertama dipicu manual di main.py, bukan di sini
        max_instances=1,      # cegah overlap kalau satu run belum selesai
        coalesce=True,
    )

    logger.info(
        "Scheduler aktif -- crawling berjalan setiap %d menit. Tekan Ctrl+C untuk berhenti.",
        config.CRAWL_INTERVAL_MINUTES,
    )
    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        logger.info("Scheduler dihentikan.")