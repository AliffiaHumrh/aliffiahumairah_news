import pandas as pd
import streamlit as st
import plotly.express as px

import config
import db

st.set_page_config(page_title="News Intelligence Dashboard", page_icon="🌸", layout="wide")

# CUSTOM STYLING (FULL SOFT PINK THEME + ACTIVE NAV BUTTONS)
st.markdown("""
<style>
    /* Google Fonts */
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700&display=swap');

    html, body, [class*="css"] {
        font-family: 'Plus Jakarta Sans', sans-serif;
    }

    /* Hide default Streamlit elements */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}

    /* Force FULL PINK Background (termasuk Header & Toolbar bawaan Streamlit) */
    .stApp, 
    header[data-testid="stHeader"],
    div[data-testid="stToolbar"],
    div[data-testid="stDecoration"] {
        background-color: #FFF5F7 !important;
    }

    header[data-testid="stHeader"] {
        background: transparent !important;
    }

    /* Sidebar Styling */
    section[data-testid="stSidebar"] {
        background-color: #FDF2F4 !important;
        border-right: 1px solid #FCE7F0 !important;
    }
    section[data-testid="stSidebar"] h1 {
        font-size: 1.35rem;
        font-weight: 700;
        color: #831843;
    }

    /* Title & Headers */
    h1 {
        font-weight: 700;
        color: #831843;
        padding-bottom: 0.4rem;
        border-bottom: 3px solid #F472B6;
        margin-bottom: 1.2rem;
        display: inline-block;
    }
    h2, h3 {
        color: #9D174D;
        font-weight: 600;
    }

    /* Cards / Containers */
    div[data-testid="stVerticalBlockBorderWrapper"] {
        background-color: #FFFFFF !important;
        border-radius: 16px !important;
        border: 1px solid #FCE7F0 !important;
        box-shadow: 0 4px 15px rgba(244, 114, 182, 0.05);
        transition: all 0.2s ease-in-out;
        padding: 0.5rem;
    }
    div[data-testid="stVerticalBlockBorderWrapper"]:hover {
        box-shadow: 0 8px 25px rgba(244, 114, 182, 0.12);
        border-color: #FBCFE8 !important;
        transform: translateY(-2px);
    }

    /* Metrics Styling */
    div[data-testid="stMetric"] {
        background-color: #FFFFFF !important;
        border: 1px solid #FCE7F0 !important;
        border-radius: 14px;
        padding: 1rem 1.2rem;
        box-shadow: 0 2px 8px rgba(244, 114, 182, 0.04);
    }
    div[data-testid="stMetricValue"] {
        color: #DB2777 !important;
        font-weight: 700;
    }
    div[data-testid="stMetricLabel"] {
        color: #9D174D !important;
        font-weight: 500;
    }

    /* Badges */
    .badge {
        display: inline-block;
        padding: 0.2rem 0.75rem;
        border-radius: 999px;
        font-size: 0.78rem;
        font-weight: 600;
        margin-right: 0.3rem;
    }
    .badge-positive { background-color: #DCFCE7; color: #166534; }
    .badge-neutral  { background-color: #F3F4F6; color: #4B5563; }
    .badge-negative { background-color: #FFE4E6; color: #9F1239; }
    .badge-unknown  { background-color: #F3F4F6; color: #9CA3AF; }
    .badge-used     { background-color: #FCE7F0; color: #9D174D; border: 1px solid #FBCFE8; }
    .badge-unused   { background-color: #FFE4E6; color: #9F1239; }
    .badge-pending  { background-color: #FEF3C7; color: #92400E; }

    /* Button Customization */
    .stButton button {
        border-radius: 10px;
        font-weight: 600;
        background-color: #FFFFFF;
        border: 1px solid #FBCFE8;
        color: #9D174D;
        transition: all 0.2s ease;
    }
    .stButton button:hover {
        background-color: #FDF2F4;
        border-color: #F472B6;
        color: #831843;
        box-shadow: 0 4px 12px rgba(244, 114, 182, 0.15);
    }
    
    /* Styling khusus tombol primary (menu aktif) */
    .stButton button[kind="primary"] {
        background-color: #F472B6 !important;
        color: #FFFFFF !important;
        border-color: #F472B6 !important;
        box-shadow: 0 4px 12px rgba(244, 114, 182, 0.3) !important;
    }

    /* Inputs, Selectbox Customization */
    .stTextInput input, .stSelectbox div[data-baseweb="select"] {
        border-radius: 10px !important;
        border-color: #FCE7F0 !important;
    }
    .stTextInput input:focus {
        border-color: #F472B6 !important;
        box-shadow: 0 0 0 1px #F472B6 !important;
    }
</style>
""", unsafe_allow_html=True)


def sentiment_badge(sentiment: str) -> str:
    label_map = {"positive": "🟢 Positif", "neutral": "⚪ Netral", "negative": "🔴 Negatif"}
    css_class = {"positive": "badge-positive", "neutral": "badge-neutral", "negative": "badge-negative"}
    label = label_map.get(sentiment, f"❔ {sentiment or 'Tidak diketahui'}")
    cls = css_class.get(sentiment, "badge-unknown")
    return f'<span class="badge {cls}">{label}</span>'


def status_badge(status: str) -> str:
    label_map = {"digunakan": "✅ Digunakan", "tidak_digunakan": "❌ Tidak digunakan", "belum_ditinjau": "⏳ Belum ditinjau"}
    css_class = {"digunakan": "badge-used", "tidak_digunakan": "badge-unused", "belum_ditinjau": "badge-pending"}
    label = label_map.get(status, status)
    cls = css_class.get(status, "badge-pending")
    return f'<span class="badge {cls}">{label}</span>'


# SIDEBAR: navigasi (button-based) + kontrol
st.sidebar.title("🌸 News Intelligence")
st.sidebar.caption(f"Database: **{config.DB_BACKEND}**")

if "page" not in st.session_state:
    st.session_state.page = "overview"

PAGES = {
    "🏠 Overview": "overview",
    "📈 Trending Topics": "trending",
    "📝 AI Summary": "summary",
    "⭐ Rekomendasi": "recommend",
    "📰 Berita": "news",
    "🔍 Model Monitoring": "monitoring",
}

st.sidebar.markdown("**Navigasi Halaman**")

for label, key_val in PAGES.items():
    is_active = (st.session_state.page == key_val)
    btn_type = "primary" if is_active else "secondary"
    
    if st.sidebar.button(label, key=f"nav_{key_val}", use_container_width=True, type=btn_type):
        st.session_state.page = key_val
        st.rerun()

page = st.session_state.page

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
def load_news(limit, source, search, date_from=None, date_to=None, sentiment=None):
    return db.fetch_news(limit=limit, source=source or None, search=search or None,
                          date_from=date_from, date_to=date_to, sentiment=sentiment or None)


@st.cache_data(ttl=300)
def load_model_logs():
    return db.get_latest_model_evaluation_logs(limit=30)


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
        st.subheader("📊 Distribusi berita per sumber")
        st.bar_chart(pd.DataFrame(by_source).set_index("source"), color="#F472B6")

        st.divider()

    col_trend, col_rec = st.columns(2)

    with col_trend:
        st.subheader("🏆 Top 5 Trending Topics")
        rising_sorted = sorted(
            [t for t in trends if (t.get("growth_rate") or 0) > 0],
            key=lambda t: -(t.get("trend_score") or 0)
        )[:5]
        if not rising_sorted:
            st.caption("Belum ada topik yang sedang naik.")
        else:
            for t in rising_sorted:
                with st.container(border=True):
                    st.markdown(f"**{t['topic_label']}**")
                    growth_pct = (t.get("growth_rate") or 0) * 100
                    st.caption(f"📈 Growth {growth_pct:.0f}% · Trend Score {t.get('trend_score', 0):.1f} · {t.get('news_count_recent', 0)} berita")

    with col_rec:
        st.subheader("⭐ Top Rekomendasi")
        top_recs = sorted(recs, key=lambda r: -(r.get("recommendation_score") or 0))[:5]
        if not top_recs:
            st.caption("Belum ada rekomendasi.")
        else:
            for r in top_recs:
                with st.container(border=True):
                    st.markdown(f"**{r['topic_label']}**")
                    st.markdown(
                        f"{sentiment_badge(r.get('dominant_sentiment', 'tidak diketahui'))} "
                        f"Skor: **{r.get('recommendation_score', 0):.0f}**",
                        unsafe_allow_html=True,
                    )

    st.divider()
    st.subheader("🆕 10 Berita Terbaru")
    recent_news = load_news(10, None, None)
    if not recent_news:
        st.caption("Belum ada berita.")
    else:
        for item in recent_news:
            with st.container(border=True):
                st.markdown(f"**[{item['title']}]({item['url']})**")
                meta = f"{item['source']}"
                if item.get("published_at"):
                    meta += f" · {item['published_at']}"
                st.caption(meta)
                if item.get("sentiment"):
                    st.markdown(sentiment_badge(item["sentiment"]), unsafe_allow_html=True)

    if not trends:
        st.info(
            "Belum ada data topik/trend. Pastikan workflow "
            "'Daily Topic Modeling, Trend Scoring, AI Summary & Recommendations' "
            "sudah pernah jalan sukses."
        )

# HALAMAN: TRENDING TOPICS
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

            st.subheader("🏆 Top 15 berdasarkan Trend Score")
            top15 = df.head(15).sort_values("trend_score", ascending=True)
            fig_top15 = px.bar(
                top15,
                x="trend_score",
                y="topic_label",
                orientation="h",
                color_discrete_sequence=["#F472B6"],
            )
            fig_top15.update_layout(
                yaxis_title="",
                xaxis_title="Trend Score",
                margin=dict(t=10, b=10, l=10, r=10),
                height=500,
            )
            st.plotly_chart(fig_top15, use_container_width=True)

# HALAMAN: AI SUMMARY
elif page == "summary":
    st.title("📝 AI Summary")
    st.caption(
        "Ringkasan bersifat EKSTRAKTIF -- disusun dari judul-judul artikel asli "
        "yang paling representatif, bukan ditulis ulang AI."
    )

    summaries = load_summaries()
    if not summaries:
        st.info("Belum ada ringkasan. Jalankan ai_summary.py dulu.")
    else:
        search_summary = st.text_input("🔎 Cari topik", placeholder="mis. korupsi, ekonomi, ...")
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

# HALAMAN: REKOMENDASI 
elif page == "recommend":
    st.title("⭐ Rekomendasi")
    st.caption(
        "Skor dihitung murni dari growth rate topik, BUKAN dari sentimen. "
        "Sentimen jadi catatan konteks, bukan alasan untuk dikecualikan."
    )

    recs = load_recommendations()

    if recs:
        sentiment_counts, status_counts = {}, {}
        for r in recs:
            s = r.get("dominant_sentiment", "tidak diketahui")
            sentiment_counts[s] = sentiment_counts.get(s, 0) + 1
            stt = r.get("status", "belum_ditinjau")
            status_counts[stt] = status_counts.get(stt, 0) + 1

        col_pie1, col_pie2 = st.columns(2)
        with col_pie1:
            st.subheader("Distribusi Sentimen")
            sentiment_color_map = {"positive": "#15803D", "neutral": "#475569", "negative": "#B91C1C", "tidak diketahui": "#94A3B8"}
            fig1 = px.pie(
                names=list(sentiment_counts.keys()), values=list(sentiment_counts.values()),
                color=list(sentiment_counts.keys()), color_discrete_map=sentiment_color_map, hole=0.4,
            )
            fig1.update_layout(margin=dict(t=10, b=10, l=10, r=10))
            st.plotly_chart(fig1, use_container_width=True)

        with col_pie2:
            st.subheader("Distribusi Status")
            status_color_map = {"digunakan": "#15803D", "tidak_digunakan": "#B91C1C", "belum_ditinjau": "#92400E"}
            fig2 = px.pie(
                names=list(status_counts.keys()), values=list(status_counts.values()),
                color=list(status_counts.keys()), color_discrete_map=status_color_map, hole=0.4,
            )
            fig2.update_layout(margin=dict(t=10, b=10, l=10, r=10))
            st.plotly_chart(fig2, use_container_width=True)

        st.divider()
    
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

        for r in filtered_recs:
            sentiment = r.get("dominant_sentiment", "tidak diketahui")
            status = r.get("status", "belum_ditinjau")

            with st.container(border=True):
                col1, col2 = st.columns([5, 1])
                with col1:
                    st.markdown(f"**{r['topic_label']}**")
                    st.write(r.get("reason", ""))
                    st.markdown(f"{sentiment_badge(sentiment)} {status_badge(status)}", unsafe_allow_html=True)
                with col2:
                    st.metric("Skor", f"{r.get('recommendation_score', 0):.0f}")

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

# HALAMAN: BERITA
elif page == "news":
    st.title("📰 Berita")
    st.write("")

    with st.container(border=True):
        st.markdown("**🔎 Filter Pencarian**")
        col_a, col_b, col_c = st.columns([2, 2, 1])
        with col_a:
            sources = load_sources()
            selected_source = st.selectbox("📡 Sumber", ["Semua sumber"] + sources)
        with col_b:
            search_news = st.text_input("🔍 Cari di judul", placeholder="mis. ekonomi, pemilu, ...")
        with col_c:
            limit_news = st.slider("🔢 Jumlah", min_value=10, max_value=2000, value=500, step=10)

        col_d, col_e = st.columns(2)
        with col_d:
            date_range = st.date_input("📅 Rentang tanggal", value=(), format="YYYY-MM-DD")
        with col_e:
            sentiment_filter = st.selectbox("😊 Sentimen", ["Semua", "positive", "neutral", "negative"])

    date_from = date_range[0].isoformat() if len(date_range) >= 1 else None
    date_to = date_range[1].isoformat() if len(date_range) >= 2 else None
    effective_limit = 2000 if (date_from or date_to) else limit_news
    sentiment_param = None if sentiment_filter == "Semua" else sentiment_filter

    source_param = None if selected_source == "Semua sumber" else selected_source
    news_items = load_news(effective_limit, source_param, search_news, date_from, date_to, sentiment_param)

    for item in news_items:
            with st.container(border=True):
                st.markdown(f"**[{item['title']}]({item['url']})**")
                st.caption(f"📡 {item['source']}")

                col_meta1, col_meta2, col_meta3 = st.columns(3)
                with col_meta1:
                    if item.get("published_at"):
                        st.caption(f"📰 Terbit: {item['published_at']}")
                with col_meta2:
                    if item.get("created_at"):
                        st.caption(f"🕒 Di-crawl: {item['created_at'][:16].replace('T', ' ')}")
                with col_meta3:
                    if item.get("topic_label"):
                        st.caption(f"🏷️ {item['topic_label']}")

                if item.get("sentiment"):
                    st.markdown(sentiment_badge(item["sentiment"]), unsafe_allow_html=True)
                content = (item.get("content") or "").strip()
                if content:
                    preview = content if len(content) < 280 else content[:280] + "..."
                    st.write(preview)

# HALAMAN: MODEL MONITORING
elif page == "monitoring":
    st.title("🔍 Model Monitoring")
    st.caption(
        "Confidence bukan akurasi asli -- akurasi butuh label manual manusia "
        "sebagai pembanding (lihat evaluate_models.py)."
    )

    if st.button("🔄 Jalankan monitoring confidence sekarang"):
        with st.spinner("Menghitung statistik confidence..."):
            import model_monitoring
            model_monitoring.main()
        st.cache_data.clear()
        st.success("Selesai! Data ter-update.")
        st.rerun()

    logs = load_model_logs()
    if not logs:
        st.info("Belum ada log. Jalankan model_monitoring.py atau evaluate_models.py dulu.")
    else:
        confidence_logs = [l for l in logs if l["log_type"] == "daily_confidence"]
        accuracy_logs = [l for l in logs if l["log_type"] == "manual_accuracy"]

        st.subheader("📊 Statistik Confidence Harian (otomatis)")
        if confidence_logs:
            df_conf = pd.DataFrame(confidence_logs).sort_values("logged_at")

            y_min = df_conf["avg_confidence"].min()
            y_max = df_conf["avg_confidence"].max()
            padding = max((y_max - y_min) * 0.3, 0.005) 

            fig_conf = px.line(df_conf, x="logged_at", y="avg_confidence", markers=True)
            fig_conf.update_traces(line_color="#F472B6", marker=dict(color="#DB2777", size=7))
            fig_conf.update_yaxes(range=[y_min - padding, y_max + padding], title="Rata-rata Confidence")
            fig_conf.update_xaxes(title="Waktu")
            fig_conf.update_layout(margin=dict(t=10, b=10, l=10, r=10))
            st.plotly_chart(fig_conf, use_container_width=True)

            st.dataframe(
                df_conf[["logged_at", "total_analyzed", "avg_confidence", "pct_low_confidence"]]
                .rename(columns={
                    "logged_at": "Waktu", "total_analyzed": "Total Dianalisis",
                    "avg_confidence": "Rata-rata Confidence", "pct_low_confidence": "% Confidence Rendah",
                }),
                use_container_width=True, hide_index=True,
            )
        else:
            st.info("Belum ada data confidence harian.")

        st.subheader("🎯 Riwayat Evaluasi Akurasi (manual)")
        if accuracy_logs:
            df_acc = pd.DataFrame(accuracy_logs).sort_values("logged_at")
            st.dataframe(
                df_acc[["logged_at", "model_name", "total_analyzed", "accuracy", "notes"]]
                .rename(columns={
                    "logged_at": "Waktu", "model_name": "Model",
                    "total_analyzed": "Sampel", "accuracy": "Akurasi", "notes": "Catatan",
                }),
                use_container_width=True, hide_index=True,
            )
        else:
            st.info("Belum ada riwayat evaluasi manual. Jalankan evaluate_models.py.")