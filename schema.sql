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

create table if not exists topic_trends (
    id                    bigint generated always as identity primary key,
    topic_id              integer not null,
    topic_label           text,
    news_count_recent     integer not null default 0,
    news_count_previous   integer not null default 0,
    growth_rate           numeric,
    trend_score           numeric,
    calculated_at         timestamptz not null default now()
);

create index if not exists idx_topic_trends_calculated_at on topic_trends (calculated_at desc);
create index if not exists idx_topic_trends_topic_id on topic_trends (topic_id);

alter table topic_trends enable row level security;
drop policy if exists "topic_trends_allow_all_internal" on topic_trends;
create policy "topic_trends_allow_all_internal"
    on topic_trends
    for all
    using (true)
    with check (true);

create or replace function bulk_update_topics(payload jsonb)
returns void as $$
  update news n
  set topic_id = (u->>'topic_id')::int,
      topic_label = u->>'topic_label'
  from jsonb_array_elements(payload) as u
  where n.id = (u->>'id')::bigint;
$$ language sql;

create table if not exists topic_summaries (
    id             bigint generated always as identity primary key,
    topic_id       integer not null,
    topic_label    text,
    summary_text   text,
    article_count  integer not null default 0,
    generated_at   timestamptz not null default now()
);

create index if not exists idx_topic_summaries_generated_at on topic_summaries (generated_at desc);
create index if not exists idx_topic_summaries_topic_id on topic_summaries (topic_id);

alter table topic_summaries enable row level security;
drop policy if exists "topic_summaries_allow_all_internal" on topic_summaries;
create policy "topic_summaries_allow_all_internal"
    on topic_summaries
    for all
    using (true)
    with check (true);

create table if not exists recommendations (
    id                     bigint generated always as identity primary key,
    topic_id               integer not null,
    topic_label            text,
    recommendation_score   numeric,
    dominant_sentiment     text,
    reason                 text,
    status                 text not null default 'belum_ditinjau',
    generated_at           timestamptz not null default now()
);

create index if not exists idx_recommendations_generated_at on recommendations (generated_at desc);
create index if not exists idx_recommendations_topic_id on recommendations (topic_id);

alter table recommendations enable row level security;
drop policy if exists "recommendations_allow_all_internal" on recommendations;
create policy "recommendations_allow_all_internal"
    on recommendations
    for all
    using (true)
    with check (true);

create table if not exists recommendations (
    id                     bigint generated always as identity primary key,
    topic_id               integer not null,
    topic_label            text,
    recommendation_score   numeric,
    status                 text,
    reason                 text,
    dominant_sentiment     text,
    created_at             timestamptz not null default now()
);

create index if not exists idx_recommendations_created_at on recommendations (created_at desc);
create index if not exists idx_recommendations_topic_id on recommendations (topic_id);

alter table recommendations enable row level security;
drop policy if exists "recommendations_allow_all_internal" on recommendations;
create policy "recommendations_allow_all_internal"
    on recommendations
    for all
    using (true)
    with check (true);

create table if not exists recommendations (
    id                    bigint generated always as identity primary key,
    topic_id              integer not null,
    topic_label           text,
    recommendation_score  numeric,
    status                text,
    reason                text,
    calculated_at         timestamptz not null default now()
);

create index if not exists idx_recommendations_calculated_at on recommendations (calculated_at desc);
create index if not exists idx_recommendations_topic_id on recommendations (topic_id);

alter table recommendations enable row level security;
drop policy if exists "recommendations_allow_all_internal" on recommendations;
create policy "recommendations_allow_all_internal"
    on recommendations
    for all
    using (true)
    with check (true);

alter table news enable row level security;

drop policy if exists "news_allow_all_internal" on news;
create policy "news_allow_all_internal"
    on news
    for all
    using (true)
    with check (true);