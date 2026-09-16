-- A deterministic editorial threshold separates actionable research events
-- from the wider immutable evidence archive. The raw archive remains intact;
-- this flag controls only the working market-moving feed.
alter table news_event_scores
  add column if not exists market_moving boolean not null default false,
  add column if not exists market_moving_reason text;

create index if not exists news_event_scores_market_moving_idx
  on news_event_scores (market_moving)
  where market_moving;
