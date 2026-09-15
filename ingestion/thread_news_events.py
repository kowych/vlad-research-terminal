"""Build conservative canonical threads over immutable news evidence events.

Only clusters with the same event type, overlapping country exposure, a
72-hour window and strong headline-token similarity are grouped automatically.
Everything else remains a one-source thread, preserving recall and auditability.
"""

from __future__ import annotations

import hashlib
import os
import re
import sys
from dataclasses import dataclass
from datetime import datetime

import psycopg

STOPWORDS = frozenset({"a", "an", "and", "are", "as", "at", "be", "by", "for", "from", "has", "in", "is", "it", "its", "of", "on", "or", "over", "says", "that", "the", "to", "with"})
WINDOW_SECONDS = 72 * 60 * 60
SIMILARITY_THRESHOLD = 0.68


@dataclass(frozen=True)
class Cluster:
    id: str
    title: str
    event_type: str
    occurred_at: datetime
    materiality: int
    countries: frozenset[str]
    tokens: frozenset[str]


def tokens(title: str) -> frozenset[str]:
    return frozenset(token for token in re.findall(r"[a-z0-9]{3,}", title.lower()) if token not in STOPWORDS)


def similar(left: Cluster, right: Cluster) -> bool:
    if left.event_type != right.event_type or not left.countries.intersection(right.countries):
        return False
    if abs((left.occurred_at - right.occurred_at).total_seconds()) > WINDOW_SECONDS:
        return False
    union = left.tokens | right.tokens
    return bool(union) and len(left.tokens & right.tokens) / len(union) >= SIMILARITY_THRESHOLD


def run(database_url: str) -> None:
    with psycopg.connect(database_url) as connection:
        with connection.cursor() as cursor:
            cursor.execute("""
              select clusters.id::text, clusters.title, clusters.event_type,
                clusters.occurred_at, clusters.materiality,
                coalesce(array_agg(countries.iso2) filter (where countries.iso2 is not null), '{}')
              from news_event_clusters clusters
              left join news_event_countries links on links.event_id = clusters.id
              left join countries on countries.id = links.country_id
              where clusters.status = 'open' and clusters.occurred_at is not null
              group by clusters.id
              order by clusters.occurred_at asc, clusters.id asc
            """)
            clusters = [Cluster(row[0], row[1], row[2], row[3], row[4], frozenset(row[5]), tokens(row[1])) for row in cursor.fetchall()]

        groups: list[list[Cluster]] = []
        for cluster in clusters:
            matching = next((group for group in reversed(groups) if similar(cluster, group[0])), None)
            if matching is None:
                groups.append([cluster])
            else:
                matching.append(cluster)

        linked = 0
        with connection.cursor() as cursor:
            for group in groups:
                leader = group[0]
                key = "automatic-v1:" + hashlib.sha256(leader.id.encode()).hexdigest()
                latest = max(item.occurred_at for item in group)
                materiality = max(item.materiality for item in group)
                cursor.execute("""
                  insert into news_event_threads (thread_key, title, event_type, occurred_at, last_occurred_at, materiality, method)
                  values (%s, %s, %s, %s, %s, %s, 'automatic-v1')
                  on conflict (thread_key) do update set
                    title = excluded.title, event_type = excluded.event_type,
                    occurred_at = excluded.occurred_at, last_occurred_at = excluded.last_occurred_at,
                    materiality = excluded.materiality, updated_at = now()
                  returning id::text
                """, (key, leader.title, leader.event_type, leader.occurred_at, latest, materiality))
                thread_id = cursor.fetchone()[0]
                for cluster in group:
                    cursor.execute("""
                      insert into news_event_thread_clusters (thread_id, cluster_id)
                      values (%s, %s)
                      on conflict (cluster_id) do update set thread_id = excluded.thread_id
                    """, (thread_id, cluster.id))
                    linked += 1
        connection.commit()
    print(f"Created or updated {len(groups)} canonical threads for {linked} immutable event clusters")


if __name__ == "__main__":
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        sys.exit("DATABASE_URL must be set. See ingestion/.env.example.")
    run(database_url)
