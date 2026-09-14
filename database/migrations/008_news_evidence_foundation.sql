create table if not exists news_feeds (
  id uuid primary key default gen_random_uuid(),
  source_id uuid not null references sources(id),
  name text not null,
  feed_url text not null unique,
  content_policy text not null check (content_policy in ('metadata_only', 'licensed_text', 'public_domain')),
  active boolean not null default true,
  last_checked_at timestamptz,
  created_at timestamptz not null default now()
);

create table if not exists raw_documents (
  id uuid primary key default gen_random_uuid(),
  source_id uuid not null references sources(id),
  feed_id uuid references news_feeds(id),
  external_id text,
  original_url text not null,
  canonical_url text not null,
  title_raw text,
  summary_raw text,
  language_code text,
  source_published_at timestamptz,
  retrieved_at timestamptz not null default now(),
  content_hash text not null,
  raw_payload jsonb not null,
  unique (source_id, external_id),
  unique (canonical_url)
);
create index if not exists raw_documents_source_time_idx on raw_documents (source_id, source_published_at desc);

create table if not exists news_articles (
  id uuid primary key default gen_random_uuid(),
  raw_document_id uuid not null unique references raw_documents(id),
  headline text not null,
  summary text,
  language_code text,
  published_at timestamptz not null,
  normalized_at timestamptz not null default now(),
  review_status text not null default 'unreviewed' check (review_status in ('unreviewed', 'approved', 'rejected'))
);
create index if not exists news_articles_published_idx on news_articles (published_at desc);

create table if not exists news_event_clusters (
  id uuid primary key default gen_random_uuid(),
  title text not null,
  event_type text not null,
  occurred_at timestamptz,
  materiality smallint not null check (materiality between 1 and 5),
  status text not null default 'open' check (status in ('open', 'resolved', 'dismissed')),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create index if not exists news_event_clusters_time_idx on news_event_clusters (occurred_at desc);

create table if not exists news_event_articles (
  event_id uuid not null references news_event_clusters(id) on delete cascade,
  article_id uuid not null references news_articles(id) on delete cascade,
  primary key (event_id, article_id)
);

create table if not exists news_event_countries (
  event_id uuid not null references news_event_clusters(id) on delete cascade,
  country_id uuid not null references countries(id),
  relevance smallint not null check (relevance between 1 and 5),
  primary key (event_id, country_id)
);

create table if not exists news_event_indicators (
  event_id uuid not null references news_event_clusters(id) on delete cascade,
  indicator_id uuid not null references indicators(id),
  direction text check (direction in ('up', 'down', 'ambiguous')),
  primary key (event_id, indicator_id)
);
