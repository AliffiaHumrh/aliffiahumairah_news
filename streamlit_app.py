"""
Dashboard AI-Based News Trend Intelligence.

Nampilin hasil dari seluruh pipeline (FR-01 s.d. FR-09): berita mentah,
topik trending, ringkasan per topik, dan rekomendasi konten. Dashboard
ini murni BACA data yang sudah dihasilkan pipeline otomatis (GitHub
Actions) -- tidak melakukan crawling/modeling apa pun sendiri.

Jalankan: streamlit run streamlit_app.py
"""

import pandas as pd
import streamlit as st

import config
import db

st.set_page_config(page_title="News Intelligence Dashboard", page_icon="📰", layout="wide")

# SIDEBAR: navigasi + kontrol
st.sidebar.title("📰 News Intelligence")
st.sidebar.caption(f"Backend: **{config.DB_BACKEND}**")

PAGES = {
    "🏠 Overview": "overview",
    "📈 Trending Topics": "trending",
    "📝 AI Summary": "summary",
    "⭐ Rekomendasi": "recommend",
    "📰 Berita": "news",
}
page_label = st.sidebar.radio("Halaman", list(PAGES.keys()), label_visibility="collapsed")
page = PAGES[page_label]

st.sidebar.divider()
if st.sidebar.button("🔄 Refresh semua data", use_container_width=True):
    st.cache_data.clear()
    st.rerun()


@st.cache_data(ttl=300)
def load_trends():
    return db.get_latest_trends(limit=100)


@st.cache_data(ttl=300)
def load_summaries():
    return db.get_latest_summaries(limit=100)


@st.cache_data(ttl=300)
def load_recommendations():
    return db.get_latest_recommendations(limit=100)


@st.cache_data(ttl=300)
def load_total_news():
    return db.count_news()


@st.cache_data(ttl=300)
def load_by_source():
    return db.count_by_source()


@st.cache_data(ttl=60)
def load_sources():
    return db.list_sources()


@st.cache_data(ttl=60)
def load_news(limit, source, search):
    return db.fetch_news(limit=limit, source=source or None, search=search or None)


# HALAMAN: OVERVIEW
if page == "overview":
    st.title("🏠 Overview")
    st.caption(
        "Data dihasilkan otomatis oleh pipeline crawling (tiap 30 menit) "
        "dan topic modeling/trend/rekomendasi (1x sehari)."
    )

    try:
        total = load_total_news()
        trends = load_trends()
        recs = load_recommendations()
    except Exception as exc:
        st.error(f"Gagal mengambil data: {exc}")
        st.stop()

    rising_count = len([t for t in trends if (t.get("growth_rate") or 0) > 0])

    col1, col2, col3 = st.columns(3)
    col1.metric("Total berita tersimpan", f"{total:,}")
    col2.metric("Topik sedang naik", rising_count)
    col3.metric("Rekomendasi aktif", len(recs))

    by_source = load_by_source()
    if by_source:
        st.subheader("Distribusi berita per sumber")
        st.bar_chart(pd.DataFrame(by_source).set_index("source"))

    if not trends:
        st.info(
            "Belum ada data topik/trend. Pastikan workflow "
            "'Daily Topic Modeling, Trend Scoring, AI Summary & Recommendations' "
            "sudah pernah jalan sukses."
        )

# HALAMAN: TRENDING TOPICS (FR-07)
elif page == "trending":
    st.title("📈 Trending Topics")
    st.caption("Dibandingkan volume berita 24 jam terakhir vs 24-48 jam sebelumnya.")

    trends = load_trends()
    if not trends:
        st.info("Belum ada data. Jalankan trend_scoring.py dulu.")
    else:
        rising = [t for t in trends if (t.get("growth_rate") or 0) > 0]
        if not rising:
            st.info("Tidak ada topik yang sedang naik saat ini.")
        else:
            df = pd.DataFrame(rising)
            df["growth_pct"] = (df["growth_rate"] * 100).round(1)
            df = df.sort_values("trend_score", ascending=False)
            st.dataframe(
                df[["topic_label", "news_count_recent", "news_count_previous", "growth_pct", "trend_score"]]
                .rename(columns={
                    "topic_label": "Topik",
                    "news_count_recent": "Berita (24 jam terakhir)",
                    "news_count_previous": "Berita (24-48 jam lalu)",
                    "growth_pct": "Growth (%)",
                    "trend_score": "Trend Score",
                }),
                use_container_width=True,
                hide_index=True,
            )

            st.subheader("Top 15 berdasarkan Trend Score")
            top15 = df.head(15).set_index("topic_label")
            st.bar_chart(top15["trend_score"])

# HALAMAN: AI SUMMARY (FR-08)
elif page == "summary":
    st.title("📝 AI Summary")
    st.caption(
        "Ringkasan bersifat EKSTRAKTIF -- disusun dari judul-judul artikel asli "
        "yang paling representatif, bukan ditulis ulang AI. Ini pilihan desain "
        "sengaja untuk menghindari risiko AI mengarang informasi (halusinasi)."
    )

    summaries = load_summaries()
    if not summaries:
        st.info("Belum ada ringkasan. Jalankan ai_summary.py dulu.")
    else:
        search_summary = st.text_input("Cari topik", placeholder="mis. korupsi, ekonomi, ...")
        filtered = [
            s for s in summaries
            if not search_summary
            or search_summary.lower() in (s.get("topic_label") or "").lower()
            or search_summary.lower() in (s.get("summary_text") or "").lower()
        ]
        filtered.sort(key=lambda s: -(s.get("article_count") or 0))

        if not filtered:
            st.warning("Tidak ada topik yang cocok dengan pencarian.")

        for s in filtered:
            with st.container(border=True):
                st.markdown(f"**{s['topic_label']}** &nbsp;·&nbsp; {s['article_count']} berita")
                st.markdown(s["summary_text"])

# HALAMAN: REKOMENDASI (FR-09)
elif page == "recommend":
    st.title("⭐ Rekomendasi")
    st.caption(
        "Skor dihitung murni dari growth rate topik (seberapa cepat topik ini "
        "sedang naik), BUKAN dari sentimen. Topik dengan sentimen negatif "
        "(misal skandal/kontroversi) tetap bisa direkomendasikan tinggi kalau "
        "memang sedang ramai -- sentimen jadi catatan konteks, bukan alasan "
        "untuk dikecualikan."
    )

    recs = load_recommendations()
    if not recs:
        st.info("Belum ada rekomendasi. Jalankan recommendation_engine.py dulu.")
    else:
        sentiment_filter = st.selectbox(
            "Filter sentimen dominan",
            ["Semua"] + sorted({r.get("dominant_sentiment", "tidak diketahui") for r in recs}),
        )
        filtered_recs = [
            r for r in recs
            if sentiment_filter == "Semua" or r.get("dominant_sentiment") == sentiment_filter
        ]
        filtered_recs.sort(key=lambda r: -(r.get("recommendation_score") or 0))

        sentiment_emoji = {"positive": "🟢", "neutral": "⚪", "negative": "🔴"}

        for r in filtered_recs:
            sentiment = r.get("dominant_sentiment", "tidak diketahui")
            emoji = sentiment_emoji.get(sentiment, "❔")
            status = r.get("status", "belum_ditinjau")
            status_emoji = {"digunakan": "✅", "tidak_digunakan": "❌", "belum_ditinjau": "⏳"}.get(status, "⏳")

            with st.container(border=True):
                col1, col2 = st.columns([5, 1])
                with col1:
                    st.markdown(f"**{r['topic_label']}**")
                    st.write(r.get("reason", ""))
                    st.caption(f"{status_emoji} Status: {status}")
                with col2:
                    st.metric("Skor", f"{r.get('recommendation_score', 0):.0f}")
                    st.markdown(f"{emoji} {sentiment}")

                btn_col1, btn_col2, btn_col3 = st.columns(3)
                with btn_col1:
                    if st.button("✅ Digunakan", key=f"used_{r['id']}", use_container_width=True):
                        db.update_recommendation_status(r["id"], "digunakan")
                        st.cache_data.clear()
                        st.rerun()
                with btn_col2:
                    if st.button("❌ Tidak digunakan", key=f"unused_{r['id']}", use_container_width=True):
                        db.update_recommendation_status(r["id"], "tidak_digunakan")
                        st.cache_data.clear()
                        st.rerun()
                with btn_col3:
                    if st.button("↩️ Reset", key=f"reset_{r['id']}", use_container_width=True):
                        db.update_recommendation_status(r["id"], "belum_ditinjau")
                        st.cache_data.clear()
                        st.rerun()

# HALAMAN: BERITA (preview mentah)
elif page == "news":
    st.title("📰 Berita")

    col_a, col_b, col_c = st.columns([2, 2, 1])
    with col_a:
        sources = load_sources()
        selected_source = st.selectbox("Sumber", ["Semua sumber"] + sources)
    with col_b:
        search_news = st.text_input("Cari di judul", placeholder="mis. ekonomi, pemilu, ...")
    with col_c:
        limit_news = st.slider("Jumlah", min_value=10, max_value=200, value=50, step=10)

    source_param = None if selected_source == "Semua sumber" else selected_source
    news_items = load_news(limit_news, source_param, search_news)

    if not news_items:
        st.warning("Tidak ada berita yang cocok dengan filter.")
    else:
        st.caption(f"{len(news_items)} berita ditampilkan")
        for item in news_items:
            with st.container(border=True):
                st.markdown(f"**[{item['title']}]({item['url']})**")
                meta = f"{item['source']}"
                if item.get("published_at"):
                    meta += f" · {item['published_at']}"
                if item.get("sentiment"):
                    meta += f" · sentimen: {item['sentiment']}"
                if item.get("topic_label"):
                    meta += f" · topik: {item['topic_label']}"
                st.caption(meta)
                content = (item.get("content") or "").strip()
                if content:
                    preview = content if len(content) < 280 else content[:280] + "..."
                    st.write(preview)