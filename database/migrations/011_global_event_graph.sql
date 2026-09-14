-- Global event graph for market-relevant news. It augments the existing
-- country evidence table instead of replacing its provenance links.

alter table news_event_countries
  add column if not exists impact_scope text not null default 'direct',
  add column if not exists confidence text not null default 'medium',
  add column if not exists transmission_note text;

alter table news_event_countries
  drop constraint if exists news_event_countries_impact_scope_check,
  add constraint news_event_countries_impact_scope_check check (impact_scope in ('direct', 'regional', 'spillover'));

alter table news_event_countries
  drop constraint if exists news_event_countries_confidence_check,
  add constraint news_event_countries_confidence_check check (confidence in ('low', 'medium', 'high'));

create index if not exists news_event_countries_country_scope_idx on news_event_countries (country_id, impact_scope);

create table if not exists news_entities (
  id uuid primary key default gen_random_uuid(),
  slug text not null unique,
  name text not null,
  entity_type text not null check (entity_type in ('person', 'government', 'institution', 'conflict', 'company', 'technology', 'commodity_group')),
  country_id uuid references countries(id),
  created_at timestamptz not null default now()
);

create table if not exists news_event_entities (
  event_id uuid not null references news_event_clusters(id) on delete cascade,
  entity_id uuid not null references news_entities(id),
  role text not null check (role in ('actor', 'subject', 'policy_maker', 'counterparty', 'affected_party')),
  primary key (event_id, entity_id, role)
);

create table if not exists market_instruments (
  id uuid primary key default gen_random_uuid(),
  slug text not null unique,
  name text not null,
  asset_class text not null check (asset_class in ('commodity', 'fx', 'rates', 'equity', 'credit', 'crypto')),
  quote_unit text,
  active boolean not null default true
);

create table if not exists news_event_market_impacts (
  event_id uuid not null references news_event_clusters(id) on delete cascade,
  instrument_id uuid not null references market_instruments(id),
  impact_scope text not null check (impact_scope in ('direct', 'spillover')),
  expected_direction text not null check (expected_direction in ('up', 'down', 'ambiguous')),
  confidence text not null check (confidence in ('low', 'medium', 'high')),
  transmission_note text not null,
  primary key (event_id, instrument_id)
);

create table if not exists news_event_scores (
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

create table if not exists news_event_market_reactions (
  event_id uuid not null references news_event_clusters(id) on delete cascade,
  instrument_id uuid not null references market_instruments(id),
  reaction_window text not null check (reaction_window in ('5m', '1h', '1d')),
  move_bps numeric,
  z_score numeric,
  measured_at timestamptz not null,
  source_url text,
  primary key (event_id, instrument_id, reaction_window)
);

-- Seed a neutral instrument vocabulary, not a price source or a trading signal.
insert into market_instruments (slug, name, asset_class, quote_unit) values
  ('brent-crude', 'Brent crude oil', 'commodity', 'USD/barrel'),
  ('wti-crude', 'WTI crude oil', 'commodity', 'USD/barrel'),
  ('ttf-natural-gas', 'TTF natural gas', 'commodity', 'EUR/MWh'),
  ('eur-usd', 'EUR / USD', 'fx', 'USD'),
  ('usd-jpy', 'USD / JPY', 'fx', 'JPY'),
  ('usd-cny', 'USD / CNY', 'fx', 'CNY'),
  ('us-10y', 'US Treasury 10-year yield', 'rates', '%'),
  ('bund-10y', 'German Bund 10-year yield', 'rates', '%'),
  ('msci-china', 'MSCI China', 'equity', 'index'),
  ('semiconductor-index', 'Global semiconductor index', 'equity', 'index')
on conflict (slug) do nothing;
