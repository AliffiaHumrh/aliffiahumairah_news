"""
Konfigurasi crawler.

Semua sumber di bawah ini menggunakan RSS resmi (sesuai PRD: "mengutamakan
RSS feed resmi dan API publik yang mengizinkan penggunaan otomatis").

Catatan per sumber:
- Detik.com MEMATIKAN RSS resmi mereka sejak akhir 2020. Tidak ada RSS
  resmi yang stabil untuk Detik saat ini, jadi TIDAK dimasukkan ke daftar
  default. Kalau tim redaksi tetap butuh Detik, opsinya: (a) cari partner
  API resmi, atau (b) crawling HTML dengan rate limiting ketat sesuai
  catatan PRD -- ini butuh maintenance lebih karena struktur HTML bisa
  berubah sewaktu-waktu.
- URL RSS media itu sendiri kadang berubah tanpa pemberitahuan. Jalankan
  `python validate_feeds.py` secara berkala (atau setiap kali crawler
  tiba-tiba mengembalikan 0 berita dari satu sumber) untuk mengecek mana
  yang masih hidup.
"""

import os

from dotenv import load_dotenv

# Baca file .env kalau ada (kredensial Supabase, dsb). Aman kalau file-nya
# tidak ada -- semua fallback ke nilai default / env var sistem.
load_dotenv()

# --------------------------------------------------------------------------
# Sumber RSS
# --------------------------------------------------------------------------
SOURCES = [
    {"name": "Antara - Terkini", "url": "https://www.antaranews.com/rss/terkini.xml"},
    {"name": "Antara - Top News", "url": "https://www.antaranews.com/rss/top-news.xml"},
    {"name": "Antara - Ekonomi & Bisnis", "url": "https://www.antaranews.com/rss/ekonomi-bisnis.xml"},
   # {"name": "CNN Indonesia - Nasional", "url": "https://www.cnnindonesia.com/nasional/rss"},
   # {"name": "CNN Indonesia - Ekonomi", "url": "https://www.cnnindonesia.com/ekonomi/rss"},
   # {"name": "CNN Indonesia - Teknologi", "url": "https://www.cnnindonesia.com/teknologi/rss"},
   # {"name": "CNBC Indonesia - News", "url": "https://www.cnbcindonesia.com/news/rss"},
   # {"name": "CNBC Indonesia - Market", "url": "https://www.cnbcindonesia.com/market/rss"},
   # {"name": "Tempo - Nasional", "url": "https://rss.tempo.co/nasional"},
   # {"name": "Tempo - Bisnis", "url": "https://rss.tempo.co/bisnis"},
    {"name": "Kumparan", "url": "https://lapi.kumparan.com/v2.0/rss/"},
    {"name": "Liputan6", "url": "https://feed.liputan6.com/rss/news"},
    {"name": "Republika", "url": "https://www.republika.co.id/rss"},
    {"name": "Media Indonesia", "url": "https://mediaindonesia.com/feed"},
    {"name": "SindoNews", "url": "https://www.sindonews.com/feed"},
    {"name": "Viva", "url": "https://www.viva.co.id/get/all"},
    {"name": "Okezone - News", "url": "http://sindikasi.okezone.com/index.php/rss/1/RSS2.0"},
    {"name": "Okezone - Economy", "url": "http://sindikasi.okezone.com/index.php/rss/11/RSS2.0"},
    {"name": "Okezone - Techno", "url": "http://sindikasi.okezone.com/index.php/rss/16/RSS2.0"}
]

CI_BLOCKED_SOURCE_NAMES = {
    "CNN Indonesia - Nasional",
    "CNN Indonesia - Ekonomi",
    "CNN Indonesia - Teknologi",
    "CNBC Indonesia - News",
    "CNBC Indonesia - Market",
    "Tempo - Nasional",
    "Tempo - Bisnis",
}

# --------------------------------------------------------------------------
# Scheduler
# --------------------------------------------------------------------------
CRAWL_INTERVAL_MINUTES = int(os.getenv("CRAWL_INTERVAL_MINUTES", 30))

# --------------------------------------------------------------------------
# HTTP behaviour (sopan ke server sumber -- lihat catatan rate limiting PRD)
# --------------------------------------------------------------------------
REQUEST_TIMEOUT_SECONDS = 15
DELAY_BETWEEN_SOURCES_SECONDS = 2
USER_AGENT = (
   "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)

# --------------------------------------------------------------------------
# Database
# --------------------------------------------------------------------------
# DB_BACKEND menentukan tempat data disimpan:
#   - "supabase" (default) -> Postgres di Supabase, bisa dibaca dashboard
#     Streamlit dari mana saja.
#   - "sqlite" -> file lokal, tidak perlu setup apapun, tapi hanya bisa
#     dibaca dari komputer yang sama (dashboard Streamlit harus jalan di
#     mesin yang sama juga).
#
# crawler.py, scheduler.py, dan streamlit_app.py semuanya cuma memanggil
# fungsi-fungsi di db/__init__.py -- tidak peduli backend mana yang aktif.
DB_BACKEND = os.getenv("DB_BACKEND", "supabase").lower()

DB_PATH = os.getenv("DB_PATH", os.path.join(os.path.dirname(__file__), "news.db"))

SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")

# --------------------------------------------------------------------------
# Logging
# --------------------------------------------------------------------------
LOG_PATH = os.getenv("LOG_PATH", os.path.join(os.path.dirname(__file__), "crawler.log"))