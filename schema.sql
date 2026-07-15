-- Jalankan file ini di Supabase Dashboard -> SQL Editor -> New query -> Run.
-- Tabel ini yang dipakai oleh crawler (tulis) dan streamlit_app.py (baca).

create table if not exists news (
    id           bigint generated always as identity primary key,
    title        text not null,
    content      text,
    processed_content text,
    source       text not null,
    url          text not null unique,
    published_at text,
    created_at   timestamptz not null default now()
);

create index if not exists idx_news_source        on news (source);
create index if not exists idx_news_published_at   on news (published_at desc);

-- MIGRASI untuk tabel yang sudah ada duluan (dibuat sebelum kolom
-- processed_content ditambahkan) -- jalankan baris ini di SQL Editor
-- Supabase kalau tabel `news` kamu sudah ada isinya:
--   alter table news add column if not exists processed_content text;

-- Aktifkan Row Level Security. Untuk tahap ini kita pakai satu policy
-- permissive (baca+tulis via anon/service key) karena crawler & dashboard
-- keduanya masih dijalankan sebagai proses internal tim, bukan diakses
-- publik langsung. Kalau nanti dashboard di-deploy publik, ganti jadi
-- policy read-only untuk anon key dan pakai service key khusus di crawler.
alter table news enable row level security;

drop policy if exists "news_allow_all_internal" on news;
create policy "news_allow_all_internal"
    on news
    for all
    using (true)
    with check (true);

-- ---------------------------------------------------------------------
-- Tabel di bawah ini BELUM dipakai kode saat ini -- disiapkan lebih awal
-- karena sudah ada di desain database PRD (topic modeling, sentiment
-- analysis, recommendation engine). Aktifkan saat mulai kerjakan FR-05
-- s.d. FR-10.
-- ---------------------------------------------------------------------

-- create table if not exists topic (
--     id           bigint generated always as identity primary key,
--     topic        text not null,
--     trend_score  numeric,
--     growth_rate  numeric,
--     created_at   timestamptz not null default now()
-- );
--
-- create table if not exists sentiment (
--     id          bigint generated always as identity primary key,
--     news_id     bigint references news(id) on delete cascade,
--     sentiment   text check (sentiment in ('positif', 'negatif', 'netral')),
--     confidence  numeric,
--     created_at  timestamptz not null default now()
-- );
--
-- create table if not exists recommendation (
--     id                    bigint generated always as identity primary key,
--     topic_id              bigint references topic(id) on delete cascade,
--     recommendation_score  numeric,
--     status                text,
--     reason                text,
--     created_at            timestamptz not null default now()
-- );