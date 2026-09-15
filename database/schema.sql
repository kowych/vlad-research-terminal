-- Muklanovich Research data platform: PostgreSQL 16+
-- Canonical database for country intelligence. Redis may be added later only as
-- a cache for API responses and generated summaries.

create extension if not exists pgcrypto;

create table countries (
  id uuid primary key default gen_random_uuid(),
  iso2 char(2) not null unique,
  iso3 char(3),
  name text not null,
  capital text,
  currency_code char(3),
  wikidata_id text unique,
  active boolean not null default true,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table sources (
  id uuid primary key default gen_random_uuid(),
  slug text not null unique,
  name text not null,
  tier smallint not null check (tier between 1 and 4),
  source_type text not null check (source_type in ('official', 'international', 'market', 'news', 'bootstrap')),
  base_url text not null,
  license_note text,
  active boolean not null default true
);

create table indicators (
  id uuid primary key default gen_random_uuid(),
  slug text not null unique,
  name text not null,
  category text not null check (category in ('growth', 'inflation', 'labour', 'policy', 'external', 'fiscal', 'market')),
  unit text not null,
  frequency text not null check (frequency in ('daily', 'weekly', 'monthly', 'quarterly', 'annual', 'event'))
);

create table source_series (
  id uuid primary key default gen_random_uuid(),
  source_id uuid not null references sources(id),
  indicator_id uuid not null references indicators(id),
  country_id uuid not null references countries(id),
  external_id text not null,
  display_name text,
  unit text,
  -- A source may publish a concept at a different cadence from the canonical
  -- indicator (for example, quarterly Australian CPI versus monthly US CPI).
  frequency text check (frequency in ('daily', 'weekly', 'monthly', 'quarterly', 'annual', 'event')),
  unique (source_id, country_id, external_id)
);

-- Each raw observation is immutable. A revision creates another row rather
-- than overwriting history, so research can be reproduced using vintage data.
create table observations (
  id uuid primary key default gen_random_uuid(),
  source_series_id uuid not null references source_series(id),
  period_start date not null,
  period_end date,
  value numeric,
  as_of_date date,
  published_at timestamptz,
  ingested_at timestamptz not null default now(),
  raw_payload jsonb,
  unique (source_series_id, period_start, as_of_date)
);
create index observations_series_period_idx on observations (source_series_id, period_start desc);

create table events (
  id uuid primary key default gen_random_uuid(),
  country_id uuid references countries(id),
  source_id uuid not null references sources(id),
  occurred_at timestamptz not null,
  headline text not null,
  original_url text not null,
  event_type text,
  market_relevance smallint check (market_relevance between 1 and 5),
  source_published_at timestamptz,
  raw_payload jsonb
);
create index events_country_time_idx on events (country_id, occurred_at desc);

-- News is stored as evidence, not as an untraceable feed. The immutable raw
-- document remains separate from its normalized article and its event cluster.
create table news_feeds (
  id uuid primary key default gen_random_uuid(),
  source_id uuid not null references sources(id),
  name text not null,
  feed_url text not null unique,
  content_policy text not null check (content_policy in ('metadata_only', 'licensed_text', 'public_domain')),
  active boolean not null default true,
  last_checked_at timestamptz,
  created_at timestamptz not null default now()
);

create table raw_documents (
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
create index raw_documents_source_time_idx on raw_documents (source_id, source_published_at desc);

create table news_articles (
  id uuid primary key default gen_random_uuid(),
  raw_document_id uuid not null unique references raw_documents(id),
  headline text not null,
  summary text,
  language_code text,
  published_at timestamptz not null,
  normalized_at timestamptz not null default now(),
  review_status text not null default 'unreviewed' check (review_status in ('unreviewed', 'approved', 'rejected'))
);
create index news_articles_published_idx on news_articles (published_at desc);

create table news_event_clusters (
  id uuid primary key default gen_random_uuid(),
  title text not null,
  event_type text not null,
  occurred_at timestamptz,
  materiality smallint not null check (materiality between 1 and 5),
  status text not null default 'open' check (status in ('open', 'resolved', 'dismissed')),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create index news_event_clusters_time_idx on news_event_clusters (occurred_at desc);

-- Research-facing canonical threads group probable duplicates while keeping
-- every source event and article separately auditable.
create table news_event_threads (
  id uuid primary key default gen_random_uuid(),
  thread_key text not null unique,
  title text not null,
  event_type text not null,
  occurred_at timestamptz not null,
  last_occurred_at timestamptz not null,
  materiality smallint not null check (materiality between 1 and 5),
  method text not null check (method in ('automatic-v1', 'manual')),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create index news_event_threads_time_idx on news_event_threads (last_occurred_at desc);

create table news_event_thread_clusters (
  thread_id uuid not null references news_event_threads(id) on delete cascade,
  cluster_id uuid not null unique references news_event_clusters(id) on delete cascade,
  primary key (thread_id, cluster_id)
);
create index news_event_thread_clusters_thread_idx on news_event_thread_clusters (thread_id);

create table news_event_articles (
  event_id uuid not null references news_event_clusters(id) on delete cascade,
  article_id uuid not null references news_articles(id) on delete cascade,
  primary key (event_id, article_id)
);

create table news_event_countries (
  event_id uuid not null references news_event_clusters(id) on delete cascade,
  country_id uuid not null references countries(id),
  relevance smallint not null check (relevance between 1 and 5),
  impact_scope text not null default 'direct' check (impact_scope in ('direct', 'regional', 'spillover')),
  confidence text not null default 'medium' check (confidence in ('low', 'medium', 'high')),
  transmission_note text,
  primary key (event_id, country_id)
);
create index news_event_countries_country_scope_idx on news_event_countries (country_id, impact_scope);

create table news_event_indicators (
  event_id uuid not null references news_event_clusters(id) on delete cascade,
  indicator_id uuid not null references indicators(id),
  direction text check (direction in ('up', 'down', 'ambiguous')),
  primary key (event_id, indicator_id)
);

-- An event may involve people, institutions, conflicts or technologies that
-- matter beyond the country in which the source was published.
create table news_entities (
  id uuid primary key default gen_random_uuid(),
  slug text not null unique,
  name text not null,
  entity_type text not null check (entity_type in ('person', 'government', 'institution', 'conflict', 'company', 'technology', 'commodity_group')),
  country_id uuid references countries(id),
  created_at timestamptz not null default now()
);

create table news_event_entities (
  event_id uuid not null references news_event_clusters(id) on delete cascade,
  entity_id uuid not null references news_entities(id),
  role text not null check (role in ('actor', 'subject', 'policy_maker', 'counterparty', 'affected_party')),
  primary key (event_id, entity_id, role)
);

-- Instruments are a small canonical market vocabulary. Provider-specific
-- tickers can be mapped here later without changing the event model.
create table market_instruments (
  id uuid primary key default gen_random_uuid(),
  slug text not null unique,
  name text not null,
  asset_class text not null check (asset_class in ('commodity', 'fx', 'rates', 'equity', 'credit', 'crypto')),
  quote_unit text,
  active boolean not null default true
);

create table news_event_market_impacts (
  event_id uuid not null references news_event_clusters(id) on delete cascade,
  instrument_id uuid not null references market_instruments(id),
  impact_scope text not null check (impact_scope in ('direct', 'spillover')),
  expected_direction text not null check (expected_direction in ('up', 'down', 'ambiguous')),
  confidence text not null check (confidence in ('low', 'medium', 'high')),
  transmission_note text not null,
  primary key (event_id, instrument_id)
);

-- Scores stay decomposed so an editor and a future model can explain why an
-- event appeared in a market-moving feed rather than treating it as a black box.
create table news_event_scores (
  event_id uuid primary key references news_event_clusters(id) on delete cascade,
  source_quality smallint not null check (source_quality between 1 and 5),
  event_significance smallint not null check (event_significance between 1 and 5),
  systemic_reach smallint not null check (systemic_reach between 1 and 5),
  freshness smallint not null check (freshness between 1 and 5),
  observed_reaction smallint check (observed_reaction between 1 and 5),
  total_score numeric(4,2) not null check (total_score between 1 and 5),
  rationale text not null,
  calculated_at timestamptz not null default now()
);

-- Immutable measured reaction, distinct from a hypothesis about direction.
create table news_event_market_reactions (
  event_id uuid not null references news_event_clusters(id) on delete cascade,
  instrument_id uuid not null references market_instruments(id),
  reaction_window text not null check (reaction_window in ('5m', '1h', '1d')),
  move_bps numeric,
  z_score numeric,
  measured_at timestamptz not null,
  source_url text,
  primary key (event_id, instrument_id, reaction_window)
);

-- Forward-looking scheduled releases. These are not news articles: they retain
-- consensus and actual values separately so a future model can reason before
-- and after the release without hindsight contamination.
create table economic_calendar_events (
  id uuid primary key default gen_random_uuid(),
  source_id uuid not null references sources(id),
  country_id uuid references countries(id),
  external_id text not null,
  title text not null,
  category text,
  scheduled_at timestamptz not null,
  timing_precision text not null default 'exact' check (timing_precision in ('exact', 'estimated', 'date_only')),
  reference_period text,
  importance smallint not null check (importance between 1 and 5),
  currency_code text,
  forecast_text text,
  previous_text text,
  actual_text text,
  forecast_value numeric,
  previous_value numeric,
  actual_value numeric,
  source_name text,
  source_url text,
  original_url text,
  status text not null default 'scheduled' check (status in ('scheduled', 'released', 'revised', 'cancelled')),
  last_updated_at timestamptz,
  raw_payload jsonb not null,
  ingested_at timestamptz not null default now(),
  unique (source_id, external_id)
);
create index economic_calendar_events_upcoming_idx on economic_calendar_events (scheduled_at asc) where status = 'scheduled';
create index economic_calendar_events_country_time_idx on economic_calendar_events (country_id, scheduled_at asc);

create table country_profiles (
  id uuid primary key default gen_random_uuid(),
  country_id uuid not null references countries(id),
  version integer not null,
  body jsonb not null,
  source_ids uuid[] not null default '{}',
  approved_at timestamptz,
  created_at timestamptz not null default now(),
  unique (country_id, version)
);

create table ai_summaries (
  id uuid primary key default gen_random_uuid(),
  country_id uuid not null references countries(id),
  regime text not null,
  confidence text not null check (confidence in ('low', 'medium', 'high')),
  summary jsonb not null,
  evidence jsonb not null,
  model_name text not null,
  prompt_version text not null,
  generated_at timestamptz not null default now(),
  valid_until timestamptz not null,
  human_reviewed_at timestamptz
);
create index ai_summaries_country_current_idx on ai_summaries (country_id, generated_at desc);

create table scenarios (
  id uuid primary key default gen_random_uuid(),
  summary_id uuid not null references ai_summaries(id) on delete cascade,
  scenario_type text not null check (scenario_type in ('base', 'upside', 'downside')),
  hypothesis text not null,
  catalysts jsonb not null,
  market_implications jsonb not null,
  invalidation text not null,
  unique (summary_id, scenario_type)
);

create table ingestion_runs (
  id uuid primary key default gen_random_uuid(),
  source_id uuid not null references sources(id),
  status text not null check (status in ('started', 'completed', 'failed')),
  started_at timestamptz not null default now(),
  completed_at timestamptz,
  records_read integer not null default 0,
  records_written integer not null default 0,
  error_message text
);
