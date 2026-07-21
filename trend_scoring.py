"""
Trend scoring (FR-07) -- growth rate internal saja, TANPA Google Trends.

Google Trends sengaja tidak dipakai: tidak ada API resmi gratis, satu-
satunya opsi (pytrends) itu scraping tidak resmi yang rapuh -- pola yang
sama dengan masalah yang berulang kali kita temui di project ini (RSS
Kompas rusak, CNN/CNBC/Tempo diblokir IP cloud). trend_score di sini
murni dari data internal (seberapa cepat jumlah berita per topik
bertambah), yang 100% dalam kendali kita dan tidak bergantung pihak luar.

Cara hitung:
1. Ambil jumlah berita per topic_id dalam 24 jam terakhir ("recent")
2. Ambil jumlah berita per topic_id dalam 24 jam SEBELUM itu ("previous")
3. growth_rate = (recent - previous) / previous
   -- kalau previous = 0 dan recent > 0, growth_rate diset 1.0 (100%,
      ditandai sebagai "topik baru muncul") supaya tidak pembagian nol
4. trend_score = growth_rate * log(1 + recent)
   -- growth_rate saja bisa menyesatkan: topik dengan previous=1,
      recent=2 punya growth_rate 100% (sama dengan previous=50,
      recent=100), padahal yang kedua jelas lebih signifikan. Mengalikan
      dengan log(1+recent) meredam noise dari topik kecil sambil tetap
      menghargai pertumbuhan cepat.

Topik dengan topic_id -1 (outlier/tidak terklasifikasi) dikecualikan --
itu bukan topik yang koheren, tidak bermakna dihitung tren-nya.

Idealnya dijalankan SETELAH topic_modeling.py (butuh topic_id sudah
terisi), jadwal harian juga -- growth rate 24 jam tidak berguna dihitung
tiap 30 menit.

Jalankan: python trend_scoring.py
"""

import logging
import math
import sys
from datetime import datetime, timedelta, timezone

import db

MIN_NEWS_FOR_TREND = 2  # topik dengan berita terlalu sedikit di-skip, noise


def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )


def compute_growth_rate(recent: int, previous: int) -> float:
    if previous == 0:
        return 1.0 if recent > 0 else 0.0
    return (recent - previous) / previous


def compute_trend_score(growth_rate: float, recent: int) -> float:
    return growth_rate * math.log(1 + recent)


def main():
    setup_logging()
    logger = logging.getLogger("news_crawler.trend_scoring")

    db.init_db()

    now = datetime.now(timezone.utc)
    recent_start = now - timedelta(hours=24)
    previous_start = now - timedelta(hours=48)

    logger.info("Menghitung jumlah berita per topik untuk periode 'recent' (24 jam terakhir)...")
    recent_counts = db.get_topic_news_counts(recent_start.isoformat(), now.isoformat())

    logger.info("Menghitung jumlah berita per topik untuk periode 'previous' (24-48 jam lalu)...")
    previous_counts = db.get_topic_news_counts(previous_start.isoformat(), recent_start.isoformat())

    all_topic_ids = set(recent_counts.keys()) | set(previous_counts.keys())
    logger.info("Total %d topik ditemukan (gabungan kedua periode).", len(all_topic_ids))

    if not all_topic_ids:
        logger.warning(
            "Tidak ada topik ditemukan di 48 jam terakhir. Pastikan "
            "topic_modeling.py sudah pernah dijalankan dan crawler "
            "sudah berjalan minimal 48 jam."
        )
        return

    batch_timestamp = now.isoformat()
    results = []

    for topic_id in all_topic_ids:
        recent_info = recent_counts.get(topic_id, {"count": 0, "label": None})
        previous_info = previous_counts.get(topic_id, {"count": 0, "label": None})

        recent_count = recent_info["count"]
        previous_count = previous_info["count"]
        label = recent_info["label"] or previous_info["label"] or f"topik_{topic_id}"

        if recent_count + previous_count < MIN_NEWS_FOR_TREND:
            continue  # terlalu sedikit data, di-skip supaya tidak jadi noise

        growth_rate = compute_growth_rate(recent_count, previous_count)
        trend_score = compute_trend_score(growth_rate, recent_count)

        db.insert_topic_trend(
            topic_id=int(topic_id),
            topic_label=label,
            count_recent=recent_count,
            count_previous=previous_count,
            growth_rate=growth_rate,
            trend_score=trend_score,
            calculated_at=batch_timestamp,
        )
        results.append((topic_id, label, recent_count, previous_count, growth_rate, trend_score))

    results.sort(key=lambda r: -r[5])

    logger.info("=== Top 10 topik trending ===")
    for topic_id, label, recent_count, previous_count, growth_rate, trend_score in results[:10]:
        logger.info(
            "  [%s] recent=%d, previous=%d, growth=%.1f%%, trend_score=%.2f",
            label, recent_count, previous_count, growth_rate * 100, trend_score,
        )

    logger.info("Selesai. Total %d topik disimpan ke topic_trends.", len(results))


if __name__ == "__main__":
    main()