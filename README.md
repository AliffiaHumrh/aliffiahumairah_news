# News Crawler — AI-Based News Trend Intelligence Dashboard

Tahap pertama dari PRD: **crawling berita otomatis & terjadwal, tersimpan
di Supabase, dan bisa ditampilkan di Streamlit** (FR-01, FR-02, baseline
FR-03). Tahap NLP (topic modeling, sentiment analysis) dan dashboard
lengkap belum termasuk di sini — itu langkah berikutnya.

## Struktur

```
news_crawler/
├── config.py            # semua pengaturan + baca kredensial dari .env
├── crawler.py           # fetch RSS, parse, dedup exact-URL, simpan
├── scheduler.py         # APScheduler — jalankan crawler tiap N menit
├── main.py              # entry point crawler + scheduler
├── validate_feeds.py    # cek cepat mana RSS yang masih hidup
├── streamlit_app.py     # dashboard preview baca data dari database
├── schema.sql           # DDL untuk dijalankan di Supabase SQL Editor
├── .env.example          # template kredensial (copy jadi .env)
├── requirements.txt
└── db/                   # layer database, bisa ganti backend tanpa
    ├── __init__.py       # ubah kode di crawler/dashboard
    ├── sqlite_backend.py
    └── supabase_backend.py
```

## Setup dari nol

### 1. Bikin project Supabase
1. Buka [supabase.com](https://supabase.com) → New Project (gratis).
2. Setelah project jadi, buka **SQL Editor** → New query → paste isi
   `schema.sql` dari folder ini → Run. Ini membuat tabel `news`.
3. Buka **Project Settings → API** → catat `Project URL` dan
   `anon public` key.

### 2. Install & konfigurasi
```bash
cd news_crawler
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env
# edit .env, isi SUPABASE_URL dan SUPABASE_KEY dengan nilai dari langkah 1
```

### 3. Jalankan crawler
```bash
python validate_feeds.py      # cek dulu RSS mana yang masih hidup
python main.py                # crawl langsung + scheduler jalan otomatis
```
Biarkan `main.py` tetap jalan di terminal/proses terpisah (atau di
server) — inilah yang membuat data terus **bertambah sesuai jadwal**
(default tiap 30 menit, atur lewat `CRAWL_INTERVAL_MINUTES` di `.env`).

### 4. Jalankan dashboard (di terminal terpisah)
```bash
streamlit run streamlit_app.py
```
Dashboard ini baca langsung dari Supabase — bisa dijalankan di komputer
lain juga, selama `.env`-nya pakai kredensial Supabase yang sama. Tidak
perlu satu proses dengan crawler.

## Kenapa dipisah jadi dua proses (crawler vs dashboard)?

Sesuai NFR di PRD ("modular: crawler, preprocessing, model, dashboard
terpisah"). Kalau dashboard-nya di-restart/crash, jadwal crawling tetap
jalan. Kalau mau lebih production-ready nanti, `main.py` bisa dijalankan
sebagai systemd service / cron / Docker container terpisah dari
Streamlit Community Cloud yang meng-host `streamlit_app.py`.

## Ganti balik ke SQLite (opsional, untuk testing tanpa akun)

Ubah satu baris di `.env`:
```
DB_BACKEND=sqlite
```
Semua kode lain (`crawler.py`, `streamlit_app.py`, dst) tidak perlu
diubah — mereka cuma bicara ke `db/__init__.py`, bukan ke backend
spesifik.

## Status terhadap Functional Requirements PRD

| ID | Status |
| --- | --- |
| FR-01 Crawling otomatis & terjadwal | ✅ Selesai (RSS + APScheduler) |
| FR-02 Penyimpanan data + metadata | ✅ Selesai, sekarang di Supabase (source, url, published_at tersimpan) |
| FR-03 Deduplikasi | ⚠️ Baseline saja: exact-match URL (unique constraint di Postgres). Cosine similarity untuk berita yang di-rewrite media lain belum ada — masuk akal dikerjakan setelah FR-04 (butuh TF-IDF/embedding). |
| FR-04 s.d. FR-12 | Belum — di luar cakupan tahap ini. |

Dashboard Streamlit saat ini = versi awal halaman **News** saja
(daftar berita + filter sumber/kata kunci + grafik jumlah per sumber).
Halaman Trending Topics, Sentiment Analysis, Recommendation, dan Model
Performance di PRD butuh FR-05 s.d. FR-12 yang belum dikerjakan.

## Catatan sumber RSS

- **Detik.com tidak punya RSS resmi yang stabil** (dimatikan sejak akhir
  2020), jadi tidak dimasukkan ke daftar default di `config.py`.
- URL RSS media Indonesia lain **kadang berubah tanpa pemberitahuan**.
  Jalankan `python validate_feeds.py` kalau salah satu sumber tiba-tiba
  0 berita terus.
- Semua fetch pakai jeda 2 detik antar-sumber (rate limiting, sesuai
  catatan di PRD supaya tidak membebani server sumber).

## Soal keamanan kredensial

`.env` berisi kunci Supabase — **jangan commit ke git** (kalau nanti
pakai git, tambahkan `.env` ke `.gitignore`) dan jangan dibagikan di
chat/screenshot. `.env.example` aman dibagikan karena isinya cuma
placeholder.

## Langkah berikutnya yang masuk akal

1. Pastikan `main.py` jalan terus (misalnya dengan `tmux`/`screen`, atau
   nanti di-deploy ke server) supaya data terus bertambah sesuai jadwal.
2. Cek `streamlit_app.py` — pastikan data yang di-crawl kelihatan di sana.
3. Setelah data cukup banyak → lanjut FR-04 (text preprocessing) sebagai
   fondasi topic modeling (BERTopic) dan sentiment analysis (IndoBERT).
4. Baru setelah itu halaman dashboard lain (Trending Topics, Sentiment,
   Recommendation) bisa mulai dibangun.