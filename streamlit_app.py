import pandas as pd
import streamlit as st
import plotly.express as px

import config
import db

st.set_page_config(page_title="News Intelligence Dashboard", layout="wide")

# CUSTOM STYLING (NEUTRAL BASE + ROSE ACCENT)
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap');

    :root {
        --bg:        #F6F7F9;
        --surface:   #FFFFFF;
        --border:    #E7E9EE;
        --border-h:  #D8DBE2;
        --text:      #111827;
        --text-med:  #4B5563;
        --text-soft: #9CA3AF;
        --rose:      #E11D48;
        --rose-dark: #BE123C;
        --rose-50:   #FFF1F3;
        --rose-200:  #FECDD3;
        --grid:      #EEF0F3;
    }

    html, body, [class*="css"] {
        font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
    }

    /* Hide default Streamlit chrome */
    #MainMenu, footer, div[data-testid="stDecoration"] { visibility: hidden; }

    .stApp,
    header[data-testid="stHeader"],
    div[data-testid="stToolbar"] {
        background-color: var(--bg) !important;
    }
    header[data-testid="stHeader"] { background: transparent !important; }
    .block-container { padding-top: 2.6rem; }

    /* ===== Sidebar ===== */
    section[data-testid="stSidebar"] {
        background-color: var(--surface) !important;
        border-right: 1px solid var(--border) !important;
    }
    .brand {
        display: flex; align-items: center; gap: 0.7rem;
        padding: 0.1rem 0 1rem;
    }
    .brand-mark {
        width: 38px; height: 38px; border-radius: 11px;
        background: linear-gradient(135deg, #F43F5E, #BE123C);
        color: #fff; font-size: 1rem;
        display: flex; align-items: center; justify-content: center;
        box-shadow: 0 6px 16px rgba(225, 29, 72, 0.25);
        flex-shrink: 0;
    }
    .brand-name { font-size: 1.02rem; font-weight: 700; color: var(--text); line-height: 1.15; }
    .brand-sub  { font-size: 0.76rem; color: var(--text-soft); font-weight: 500; }
    .nav-label {
        font-size: 0.72rem; font-weight: 700; letter-spacing: 0.1em;
        text-transform: uppercase; color: var(--text-soft);
        margin: 0.3rem 0 0.5rem;
    }

    /* ===== Page header ===== */
    .page-header {
        margin-bottom: 1.1rem; padding-bottom: 0.8rem;
        border-bottom: 1px solid var(--border);
    }
    .page-kicker {
        font-size: 0.72rem; font-weight: 700; letter-spacing: 0.12em;
        text-transform: uppercase; color: var(--rose); margin-bottom: 0.2rem;
    }
    .page-title { font-size: 1.9rem; font-weight: 700; color: var(--text); margin: 0; line-height: 1.2; }

    h1 { border: none; padding: 0; }
    h2, h3 { color: var(--text); font-weight: 700; }

    /* ===== Cards / Containers ===== */
    div[data-testid="stVerticalBlockBorderWrapper"] {
        background-color: var(--surface) !important;
        border-radius: 14px !important;
        border: 1px solid var(--border) !important;
        box-shadow: 0 1px 2px rgba(16, 24, 40, 0.04);
        transition: box-shadow 0.18s ease, border-color 0.18s ease;
        padding: 0.4rem;
    }
    div[data-testid="stVerticalBlockBorderWrapper"]:hover {
        box-shadow: 0 8px 24px rgba(16, 24, 40, 0.08);
        border-color: var(--border-h) !important;
    }

    /* ===== Metrics ===== */
    div[data-testid="stMetric"] {
        background-color: var(--surface) !important;
        border: 1px solid var(--border) !important;
        border-radius: 12px;
        padding: 1rem 1.2rem;
    }
    div[data-testid="stMetricValue"] { color: var(--rose) !important; font-weight: 700; }
    div[data-testid="stMetricLabel"] { color: var(--text-med) !important; font-weight: 600; }

    /* ===== Badges ===== */
    .badge {
        display: inline-block;
        padding: 0.2rem 0.7rem;
        border-radius: 999px;
        font-size: 0.76rem;
        font-weight: 600;
        margin-right: 0.3rem;
    }
    .badge-positive { background-color: #ECFDF5; color: #047857; }
    .badge-neutral  { background-color: #F1F5F9; color: #475569; }
    .badge-negative { background-color: #FEF2F2; color: #B91C1C; }
    .badge-unknown  { background-color: #F1F5F9; color: #94A3B8; }
    .badge-used     { background-color: var(--rose-50); color: var(--rose-dark); border: 1px solid var(--rose-200); }
    .badge-unused   { background-color: #FEF2F2; color: #B91C1C; }
    .badge-pending  { background-color: #FFFBEB; color: #B45309; }

    /* ===== Buttons ===== */
    .stButton button {
        border-radius: 9px;
        font-weight: 600;
        background-color: var(--surface);
        border: 1px solid var(--border);
        color: var(--text-med);
        transition: all 0.16s ease;
    }
    .stButton button:hover {
        background-color: var(--rose-50);
        border-color: var(--rose);
        color: var(--rose);
    }
    .stButton button[kind="primary"] {
        background-color: var(--rose) !important;
        color: #FFFFFF !important;
        border-color: var(--rose) !important;
        box-shadow: 0 4px 12px rgba(225, 29, 72, 0.25) !important;
    }
    .stButton button[kind="primary"]:hover {
        background-color: var(--rose-dark) !important;
        border-color: var(--rose-dark) !important;
    }

    /* ===== Inputs ===== */
    .stTextInput input, .stSelectbox div[data-baseweb="select"] {
        border-radius: 9px !important;
        border-color: var(--border) !important;
    }
    .stTextInput input:focus {
        border-color: var(--rose) !important;
        box-shadow: 0 0 0 1px var(--rose) !important;
    }

    /* ===== Stat Cards (Overview) ===== */
    div[class*="st-key-stat_"] div[data-testid="stVerticalBlockBorderWrapper"] {
        min-height: 210px;
        display: flex;
        flex-direction: column;
        justify-content: space-between;
    }
    .stat-card {
        text-align: center;
        padding: 0.8rem 0.4rem 0.2rem;
    }
    .stat-card .stat-icon {
        font-size: 1.5rem;
        line-height: 1;
    }
    .stat-card .stat-value {
        font-size: 2.3rem;
        font-weight: 800;
        color: var(--text);
        line-height: 1.1;
        margin-top: 0.4rem;
    }
    .stat-card .stat-label {
        font-size: 0.92rem;
        font-weight: 600;
        color: var(--text-med);
        margin-top: 0.25rem;
    }
    .stat-card .stat-caption {
        font-size: 0.75rem;
        color: var(--text-soft);
        margin-top: 0.3rem;
    }
    div[class*="st-key-stat_"] .stButton button {
        background-color: var(--surface);
        border: 1px solid var(--border);
        color: var(--rose);
        font-size: 0.82rem;
        font-weight: 600;
        padding: 0.3rem 0.6rem;
        margin-top: 0.5rem;
    }
    div[class*="st-key-stat_"] .stButton button:hover {
        background-color: var(--rose);
        border-color: var(--rose);
        color: #FFFFFF;
    }

    /* ===== Expander ===== */
    div[data-testid="stExpander"] {
        border: 1px solid var(--border) !important;
        border-radius: 11px !important;
        background-color: var(--surface) !important;
        margin-bottom: 0.5rem;
        box-shadow: 0 1px 2px rgba(16, 24, 40, 0.04);
        transition: all 0.16s ease;
    }
    div[data-testid="stExpander"]:hover {
        border-color: var(--border-h) !important;
        box-shadow: 0 6px 18px rgba(16, 24, 40, 0.07);
    }
    div[data-testid="stExpander"] summary {
        font-weight: 600 !important;
        color: var(--text) !important;
        border-radius: 11px !important;
    }
    div[data-testid="stExpander"] summary:hover { color: var(--rose) !important; }
    div[data-testid="stExpander"] summary svg { fill: var(--rose) !important; }

    /* ===== Misc ===== */
    div[data-testid="stDataFrame"] { border: 1px solid var(--border); border-radius: 11px; }
    hr { margin: 1.1rem 0; border-color: var(--border); }
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


# Konsistensi tampilan: header halaman & styling chart
ROSE = "#E11D48"
ROSE_SEQUENCE = ["#E11D48", "#FB7185", "#F9A8D4", "#9D174D", "#FBCFE8"]
_PLOT_FONT = dict(family="Plus Jakarta Sans, sans-serif", color="#4B5563", size=12)


def page_header(title: str):
    """Header konsisten di tiap halaman: kicker brand + judul besar + garis pemisah."""
    st.markdown(
        f'<div class="page-header">'
        f'<div class="page-kicker">News Intelligence</div>'
        f'<div class="page-title">{title}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )


def style_fig(fig, *, height=None):
    """Samakan gaya semua chart Plotly: font, background transparan, grid halus."""
    fig.update_layout(
        font=_PLOT_FONT,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(t=10, b=10, l=10, r=10),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0, title=None),
    )
    fig.update_xaxes(gridcolor="#EEF0F3", zerolinecolor="#EEF0F3")
    fig.update_yaxes(gridcolor="#EEF0F3", zerolinecolor="#EEF0F3")
    if height is not None:
        fig.update_layout(height=height)
    return fig


@st.cache_data(ttl=300)
def load_topic_articles(topic_id, limit=6):
    return db.get_articles_for_topic(topic_id, limit=limit)


def render_topic_articles(topic_id):
    """Tampilkan daftar berita yang masuk ke satu topik (dipakai di kartu Overview)."""
    if topic_id is None:
        st.caption("Topik ini tidak punya ID, beritanya tidak bisa ditarik.")
        return
    articles = load_topic_articles(topic_id)
    if not articles:
        st.caption("Belum ada berita yang terkait topik ini.")
        return
    for a in articles:
        title = a.get("title") or "(tanpa judul)"
        url = a.get("url")
        st.markdown(f"**[{title}]({url})**" if url else f"**{title}**")
        content = (a.get("content") or "").strip()
        preview = content if len(content) <= 160 else content[:160] + "..."
        parts = []
        if a.get("sentiment"):
            parts.append(sentiment_badge(a["sentiment"]))
        if preview:
            parts.append(f'<span style="color:#9CA3AF;font-size:0.8rem;">{preview}</span>')
        if parts:
            st.markdown(" ".join(parts), unsafe_allow_html=True)


def stat_card(column, *, key, icon, value, label, caption, target_page=None, cta="Lihat detail →"):
    """Kartu statistik untuk Overview. Kalau target_page diisi, muncul tombol yang pindah halaman."""
    with column:
        with st.container(border=True, key=key):
            st.markdown(
                f'''
                <div class="stat-card">
                    <div class="stat-icon">{icon}</div>
                    <div class="stat-value">{value}</div>
                    <div class="stat-label">{label}</div>
                    <div class="stat-caption">{caption}</div>
                </div>
                ''',
                unsafe_allow_html=True,
            )
            if target_page and st.button(cta, key=f"{key}_btn", use_container_width=True):
                st.session_state.page = target_page
                st.rerun()


# SIDEBAR: navigasi (button-based) + kontrol
st.sidebar.markdown(
    '<div class="brand">'
    '<div><div class="brand-name">News Intelligence</div>'
    '<div class="brand-sub">Analytics Dashboard</div></div>'
    '</div>',
    unsafe_allow_html=True,
)

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

st.sidebar.markdown('<div class="nav-label">Navigasi</div>', unsafe_allow_html=True)

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
def load_topics():
    return db.list_topics()


@st.cache_data(ttl=60)
def load_news(limit, source, search, date_from=None, date_to=None, sentiment=None, topic=None):
    return db.fetch_news(limit=limit, source=source or None, search=search or None,
                          date_from=date_from, date_to=date_to, sentiment=sentiment or None,
                          topic=topic or None)


@st.cache_data(ttl=300)
def load_model_logs():
    return db.get_latest_model_evaluation_logs(limit=30)


# HALAMAN: OVERVIEW
if page == "overview":
    page_header("🏠 Overview")
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

    col1, col2, col3 = st.columns(3, gap="medium")
    stat_card(
        col1, key="stat_total",
        icon="📰", value=f"{total:,}", label="Total berita tersimpan",
        caption="Seluruh berita hasil crawling",
        target_page="news", cta="Lihat berita →",
    )
    stat_card(
        col2, key="stat_trending",
        icon="📈", value=rising_count, label="Topik sedang naik",
        caption="Topik dengan growth rate positif",
        target_page="trending", cta="Lihat topik tren →",
    )
    stat_card(
        col3, key="stat_recommend",
        icon="⭐", value=len(recs), label="Rekomendasi aktif",
        caption="Topik yang direkomendasikan untuk diliput",
        target_page="recommend", cta="Lihat rekomendasi →",
    )

    by_source = load_by_source()
    if by_source:
        st.subheader("📊 Distribusi berita per sumber")
        st.bar_chart(pd.DataFrame(by_source).set_index("source"), color=ROSE)

        st.divider()

    col_trend, col_rec = st.columns(2)

    with col_trend:
        st.subheader("🏆 Top 5 Trending Topics")
        st.caption("Klik topik untuk melihat berita yang berkaitan.")
        rising_sorted = sorted(
            [t for t in trends if (t.get("growth_rate") or 0) > 0],
            key=lambda t: -(t.get("trend_score") or 0)
        )[:5]
        if not rising_sorted:
            st.caption("Belum ada topik yang sedang naik.")
        else:
            for t in rising_sorted:
                growth_pct = (t.get("growth_rate") or 0) * 100
                with st.expander(f"{t['topic_label']}  ·  📈 {growth_pct:.0f}%"):
                    st.caption(
                        f"Trend Score {t.get('trend_score', 0):.1f} · "
                        f"{t.get('news_count_recent', 0)} berita (24 jam terakhir)"
                    )
                    render_topic_articles(t.get("topic_id"))

    with col_rec:
        st.subheader("⭐ Top Rekomendasi")
        st.caption("Klik topik untuk melihat berita yang berkaitan.")
        top_recs = sorted(recs, key=lambda r: -(r.get("recommendation_score") or 0))[:5]
        if not top_recs:
            st.caption("Belum ada rekomendasi.")
        else:
            for r in top_recs:
                with st.expander(f"{r['topic_label']}  ·  ⭐ {r.get('recommendation_score', 0):.0f}"):
                    st.markdown(
                        f"{sentiment_badge(r.get('dominant_sentiment', 'tidak diketahui'))} "
                        f"Skor rekomendasi: **{r.get('recommendation_score', 0):.0f}**",
                        unsafe_allow_html=True,
                    )
                    if r.get("reason"):
                        st.caption(r["reason"])
                    render_topic_articles(r.get("topic_id"))

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
    page_header("📈 Trending Topics")
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
                color_discrete_sequence=[ROSE],
            )
            fig_top15.update_layout(yaxis_title="", xaxis_title="Trend Score")
            style_fig(fig_top15, height=500)
            st.plotly_chart(fig_top15, use_container_width=True)

            st.divider()
            st.subheader("📰 Berita per topik")
            st.caption("Klik topik untuk melihat berita yang berkaitan.")
            for t in df.to_dict("records"):
                header = (
                    f"{t['topic_label']}  ·  📈 {t.get('growth_pct', 0):.0f}%  "
                    f"·  Trend Score {t.get('trend_score', 0):.1f}"
                )
                with st.expander(header):
                    st.caption(
                        f"{t.get('news_count_recent', 0)} berita (24 jam terakhir) vs "
                        f"{t.get('news_count_previous', 0)} berita (24-48 jam lalu)"
                    )
                    render_topic_articles(t.get("topic_id"))

# HALAMAN: AI SUMMARY
elif page == "summary":
    page_header("📝 AI Summary")
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
    page_header("⭐ Rekomendasi")
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
            style_fig(fig1)
            st.plotly_chart(fig1, use_container_width=True)

        with col_pie2:
            st.subheader("Distribusi Status")
            status_color_map = {"digunakan": "#15803D", "tidak_digunakan": "#B91C1C", "belum_ditinjau": "#92400E"}
            fig2 = px.pie(
                names=list(status_counts.keys()), values=list(status_counts.values()),
                color=list(status_counts.keys()), color_discrete_map=status_color_map, hole=0.4,
            )
            style_fig(fig2)
            st.plotly_chart(fig2, use_container_width=True)

        st.divider()
    
    if not recs:
        st.info("Belum ada rekomendasi. Jalankan recommendation_engine.py dulu.")
    else:
        STATUS_LABELS = {
            "digunakan": "✅ Digunakan",
            "tidak_digunakan": "❌ Tidak digunakan",
            "belum_ditinjau": "⏳ Belum ditinjau",
        }

        col_f1, col_f2 = st.columns(2)
        with col_f1:
            sentiment_filter = st.selectbox(
                "Filter sentimen dominan",
                ["Semua"] + sorted({r.get("dominant_sentiment", "tidak diketahui") for r in recs}),
            )
        with col_f2:
            status_options = ["Semua"] + [
                s for s in ["digunakan", "tidak_digunakan", "belum_ditinjau"]
                if any(r.get("status", "belum_ditinjau") == s for r in recs)
            ]
            status_filter = st.selectbox(
                "Filter status",
                status_options,
                format_func=lambda s: "Semua status" if s == "Semua" else STATUS_LABELS.get(s, s),
            )

        filtered_recs = [
            r for r in recs
            if (sentiment_filter == "Semua" or r.get("dominant_sentiment") == sentiment_filter)
            and (status_filter == "Semua" or r.get("status", "belum_ditinjau") == status_filter)
        ]
        filtered_recs.sort(key=lambda r: -(r.get("recommendation_score") or 0))

        st.caption(f"Menampilkan **{len(filtered_recs)}** dari {len(recs)} rekomendasi.")

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
    page_header("📰 Berita")
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

        col_d, col_e, col_f = st.columns(3)
        with col_d:
            date_range = st.date_input("📅 Rentang tanggal", value=(), format="YYYY-MM-DD")
        with col_e:
            sentiment_filter = st.selectbox("😊 Sentimen", ["Semua", "positive", "neutral", "negative"])
        with col_f:
            search_topic = st.text_input("🏷️ Topik", placeholder="mis. 11_sekolah_persib_...")

    date_from = date_range[0].isoformat() if len(date_range) >= 1 else None
    date_to = date_range[1].isoformat() if len(date_range) >= 2 else None
    effective_limit = 2000 if (date_from or date_to) else limit_news
    sentiment_param = None if sentiment_filter == "Semua" else sentiment_filter
    topic_param = search_topic.strip() or None

    source_param = None if selected_source == "Semua sumber" else selected_source
    news_items = load_news(effective_limit, source_param, search_news, date_from, date_to,
                           sentiment_param, topic_param)

    export_cols = ["title", "url", "source", "published_at", "created_at",
                   "topic_label", "sentiment", "content"]
    col_count, col_dl = st.columns([3, 1])
    with col_count:
        st.caption(f"Ditemukan **{len(news_items)}** berita sesuai filter.")
    with col_dl:
        if news_items:
            df_export = pd.DataFrame(news_items)
            df_export = df_export[[c for c in export_cols if c in df_export.columns]]
            csv_bytes = df_export.to_csv(index=False).encode("utf-8-sig")
            st.download_button(
                "⬇️ Download CSV",
                data=csv_bytes,
                file_name=f"berita_{pd.Timestamp.now():%Y%m%d_%H%M}.csv",
                mime="text/csv",
                use_container_width=True,
            )

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
    page_header("🔍 Model Monitoring")
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
            fig_conf.update_traces(line_color=ROSE, marker=dict(color="#BE123C", size=7))
            fig_conf.update_yaxes(range=[y_min - padding, y_max + padding], title="Rata-rata Confidence")
            fig_conf.update_xaxes(title="Waktu")
            style_fig(fig_conf)
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