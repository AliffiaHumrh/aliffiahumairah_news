"""
Facade database. Semua kode lain (crawler.py, scheduler.py, main.py,
streamlit_app.py) import dari sini saja: `import db`, lalu panggil
`db.insert_news(...)`, `db.fetch_news(...)`, dst.

Backend aktif ditentukan oleh config.DB_BACKEND ("supabase" atau
"sqlite"). Ganti backend cukup lewat .env, tidak perlu ubah kode lain.
"""

import logging

import config

logger = logging.getLogger("news_crawler.db")

if config.DB_BACKEND == "supabase":
    from db import supabase_backend as _backend
elif config.DB_BACKEND == "sqlite":
    from db import sqlite_backend as _backend
else:
    raise ValueError(
        f"DB_BACKEND tidak dikenal: '{config.DB_BACKEND}'. "
        "Gunakan 'supabase' atau 'sqlite' di .env."
    )

logger.info("Database backend aktif: %s", config.DB_BACKEND)

init_db = _backend.init_db
url_exists = _backend.url_exists
insert_news = _backend.insert_news
count_news = _backend.count_news
count_by_source = _backend.count_by_source
fetch_news = _backend.fetch_news
list_sources = _backend.list_sources
get_unprocessed_news = _backend.get_unprocessed_news
update_processed_content = _backend.update_processed_content