-- A thread is a research-facing canonical event. Individual source events and
-- articles remain immutable evidence; a thread only groups probable duplicates.
create table if not exists news_event_threads (
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
create index if not exists news_event_threads_time_idx on news_event_threads (last_occurred_at desc);

create table if not exists news_event_thread_clusters (
  thread_id uuid not null references news_event_threads(id) on delete cascade,
  cluster_id uuid not null unique references news_event_clusters(id) on delete cascade,
  primary key (thread_id, cluster_id)
);
create index if not exists news_event_thread_clusters_thread_idx on news_event_thread_clusters (thread_id);
