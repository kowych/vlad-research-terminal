-- The active feed has two deliberate tiers: strict market-moving events and
-- broader research signals. Both remain narrower than the raw evidence archive.
alter table news_event_scores
  add column if not exists research_relevant boolean not null default false,
  add column if not exists research_relevance_reason text;

create index if not exists news_event_scores_research_relevant_idx
  on news_event_scores (research_relevant)
  where research_relevant;
