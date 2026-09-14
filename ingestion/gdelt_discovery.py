"""Collect recent global-news metadata from GDELT as discovery evidence only.

No article body is fetched. Every UI item links to the original publisher and
is labelled discovery-only until corroborated by an authorised source.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from datetime import UTC, datetime
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from urllib.error import HTTPError

import psycopg

QUERIES = {"global-macro-risk": "(Trump OR White House OR Iran OR Hormuz OR Ukraine OR Russia OR China) (oil OR conflict OR attack OR strike OR sanctions OR semiconductor OR chip OR AI OR technology OR export)"}


def fetch(query: str, hours: int) -> list[dict[str, object]]:
    params = urlencode({"query": query, "mode": "artlist", "format": "json", "maxrecords": 25, "timespan": f"{hours}h", "format": "json"})
    url = f"https://api.gdeltproject.org/api/v2/doc/doc?{params}"
    try:
        with urlopen(Request(url, headers={"User-Agent": "Muklanovich-Research/0.1 (discovery metadata only)"}), timeout=30) as response:
            payload = json.loads(response.read())
    except HTTPError as error:
        if error.code == 429:
            print("GDELT rate limit reached; keeping prior evidence and retrying on the next scheduled run.")
            return []
        raise
    return payload.get("articles", []) if isinstance(payload, dict) else []


def occurred_at(value: object) -> datetime:
    if isinstance(value, str):
        try:
            return datetime.strptime(value, "%Y%m%dT%H%M%SZ").replace(tzinfo=UTC)
        except ValueError:
            pass
    return datetime.now(UTC)


def run(database_url: str, hours: int) -> None:
    with psycopg.connect(database_url) as connection:
        with connection.cursor() as cursor:
            cursor.execute("select id::text from sources where slug = 'gdelt-discovery'")
            row = cursor.fetchone()
            if not row:
                raise RuntimeError("Apply database/migrations/013_news_source_expansion.sql first.")
            source_id = row[0]
        written = 0
        for theme, query in QUERIES.items():
            for article in fetch(query, hours):
                url = article.get("url")
                title = article.get("title")
                if not isinstance(url, str) or not isinstance(title, str):
                    continue
                external_id = hashlib.sha256(url.encode()).hexdigest()
                payload = {"theme": theme, "gdelt": article}
                with connection.cursor() as cursor:
                    cursor.execute("""
                      insert into raw_documents (source_id, external_id, original_url, canonical_url, title_raw, language_code, source_published_at, content_hash, raw_payload)
                      values (%s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb)
                      on conflict (canonical_url) do nothing returning id
                    """, (source_id, external_id, url, url, title, article.get("language"), occurred_at(article.get("seendate")), external_id, json.dumps(payload)))
                    raw = cursor.fetchone()
                    if not raw:
                        continue
                    cursor.execute("insert into news_articles (raw_document_id, headline, language_code, published_at) values (%s, %s, %s, %s)", (raw[0], title, article.get("language"), occurred_at(article.get("seendate"))))
                    written += 1
            connection.commit()
    print(f"Imported {written} GDELT discovery records from the last {hours} hours")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--hours", type=int, default=24, help="Lookback window in hours; default: 24")
    args = parser.parse_args()
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        sys.exit("DATABASE_URL must be set. See ingestion/.env.example.")
    run(database_url, args.hours)
