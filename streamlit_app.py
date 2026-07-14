"""
Dashboard preview untuk data hasil crawling.

Ini BUKAN dashboard final di PRD (yang punya halaman Trending Topics,
Sentiment Analysis, Recommendation, dst -- itu butuh FR-05 s.d. FR-10
yang belum dikerjakan). Ini cuma halaman "News" versi awal: menampilkan
berita yang berhasil di-crawl, supaya kamu bisa lihat crawler benar-benar
bekerja dan datanya tersimpan di Supabase.

Jalankan terpisah dari crawler:
    streamlit run streamlit_app.py

Crawler (main.py) dan dashboard ini TIDAK perlu jalan di proses yang
sama -- dashboard cuma baca dari Supabase, jadi bisa dijalankan kapan
saja, di komputer manapun, selama .env-nya benar.
"""

import pandas as pd
import streamlit as st

import config
import db

st.set_page_config(page_title="News Crawler — Preview", page_icon="📰", layout="wide")

st.title("📰 News Crawler — Preview Data")
st.caption(
    f"Backend database: **{config.DB_BACKEND}** · "
    "Halaman ini menampilkan berita mentah hasil crawling. "
    "Topik, sentimen, dan rekomendasi menyusul di tahap berikutnya."
)


@st.cache_data(ttl=60)
def load_sources():
    try:
        return db.list_sources()
    except Exception as exc:
        st.error(f"Gagal konek ke database: {exc}")
        return []


@st.cache_data(ttl=60)
def load_news(limit, source, search):
    return db.fetch_news(limit=limit, source=source or None, search=search or None)


@st.cache_data(ttl=60)
def load_summary():
    return db.count_news(), db.count_by_source()


# --- Sidebar: filter ---
st.sidebar.header("Filter")

sources = load_sources()
selected_source = st.sidebar.selectbox("Sumber", ["Semua sumber"] + sources)
search_term = st.sidebar.text_input("Cari di judul", placeholder="mis. ekonomi, pemilu, ...")
limit = st.sidebar.slider("Jumlah berita ditampilkan", min_value=10, max_value=200, value=50, step=10)

if st.sidebar.button("🔄 Refresh data"):
    st.cache_data.clear()
    st.rerun()

# --- Ringkasan ---
try:
    total, by_source = load_summary()
except Exception as exc:
    st.error(
        "Tidak bisa mengambil data. Pastikan crawler sudah pernah dijalankan "
        f"minimal sekali dan .env sudah benar.\n\nDetail: {exc}"
    )
    st.stop()

col1, col2 = st.columns([1, 3])
with col1:
    st.metric("Total berita tersimpan", total)
with col2:
    if by_source:
        st.bar_chart(pd.DataFrame(by_source).set_index("source"))
    else:
        st.info("Belum ada data. Jalankan `python main.py` dulu untuk mulai crawling.")

st.divider()

# --- Tabel berita ---
source_filter = None if selected_source == "Semua sumber" else selected_source
news_items = load_news(limit, source_filter, search_term)

if not news_items:
    st.warning("Tidak ada berita yang cocok dengan filter saat ini.")
else:
    st.subheader(f"Berita terbaru ({len(news_items)} ditampilkan)")
    for item in news_items:
        with st.container(border=True):
            st.markdown(f"**[{item['title']}]({item['url']})**")
            meta = f"{item['source']}"
            if item.get("published_at"):
                meta += f" · {item['published_at']}"
            st.caption(meta)
            content = (item.get("content") or "").strip()
            if content:
                preview = content if len(content) < 280 else content[:280] + "..."
                st.write(preview)