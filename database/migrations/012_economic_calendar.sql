-- Scheduled macro releases are intentionally separate from published news.
-- This makes forecast-versus-actual analysis reproducible and prevents future
-- information from leaking into an as-of research brief.

insert into sources (slug, name, tier, source_type, base_url, license_note)
values ('trading-economics-calendar', 'Trading Economics Economic Calendar', 3, 'market', 'https://api.tradingeconomics.com/', 'Licensed API required; preserve the linked official source where supplied.')
on conflict (slug) do update set name = excluded.name, tier = excluded.tier, source_type = excluded.source_type, base_url = excluded.base_url, license_note = excluded.license_note;

create table if not exists economic_calendar_events (
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
create index if not exists economic_calendar_events_upcoming_idx on economic_calendar_events (scheduled_at asc) where status = 'scheduled';
create index if not exists economic_calendar_events_country_time_idx on economic_calendar_events (country_id, scheduled_at asc);
