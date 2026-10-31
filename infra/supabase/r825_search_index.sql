-- R-825: الفهرس الذاتي لمحرك البحث — كل صفحة قرأها المحرك تُحفظ وتصبح قابلة للبحث فورًا
-- (محرك ينمو مع كل سؤال) + ذاكرة إجابات مؤقتة بمهلة صلاحية (قصيرة للأسئلة الآنية).
-- يُطبَّق مرة واحدة (idempotent) عبر واجهة إدارة Supabase أو محرر SQL.
create table if not exists public.search_pages (
  url          text primary key,
  title        text not null default '',
  lang         text not null default '',
  provider     text not null default '',
  body         text not null default '',
  published_at timestamptz,
  fetched_at   timestamptz not null default now(),
  hits         integer not null default 0,
  fts          tsvector generated always as
               (to_tsvector('simple', coalesce(title, '') || ' ' || coalesce(body, ''))) stored
);
create index if not exists search_pages_fts_idx on public.search_pages using gin (fts);
create index if not exists search_pages_fetched_idx on public.search_pages (fetched_at desc);

create table if not exists public.search_cache (
  key         text primary key,
  payload     jsonb not null,
  created_at  timestamptz not null default now(),
  ttl_seconds integer not null default 3600
);

alter table public.search_pages enable row level security;
alter table public.search_cache enable row level security;

-- بحث نصي مرتب (OR بين المصطلحات + بادئة) — حتمي، يُستدعى عبر PostgREST /rpc/search_pages_query
create or replace function public.search_pages_query(terms text[], lim integer default 10,
                                                     max_age_days integer default 3650)
returns table (url text, title text, lang text, provider text, body text,
               published_at timestamptz, fetched_at timestamptz, rank real)
language sql stable as $$
  with q as (
    select to_tsquery('simple', string_agg(quote_literal(lower(t)) || ':*', ' | ')) as tsq
    from unnest(terms) as t where length(t) > 1
  )
  select p.url, p.title, p.lang, p.provider, left(p.body, 20000), p.published_at, p.fetched_at,
         ts_rank_cd(p.fts, q.tsq) as rank
  from public.search_pages p, q
  where q.tsq is not null and p.fts @@ q.tsq
    and p.fetched_at > now() - make_interval(days => max_age_days)
  order by rank desc, p.fetched_at desc
  limit greatest(1, least(lim, 50));
$$;
