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

# One deliberately broad, low-frequency request is safer than many country
# queries against GDELT's shared public endpoint.  Country assignment happens
# after ingestion in classify_news.py, where cross-border transmission is also
# explicit and auditable.
QUERIES = {
    "global-macro-risk": "(Trump OR \"White House\" OR Iran OR Hormuz OR Ukraine OR Russia OR China) (oil OR energy OR conflict OR attack OR strike OR sanctions OR tariff OR trade OR semiconductor OR chip OR AI OR technology OR export OR nuclear)"
}


def fetch(query: str, hours: int, limit: int) -> list[dict[str, object]]:
    params = urlencode({"query": query, "mode": "artlist", "format": "json", "maxrecords": limit, "timespan": f"{hours}h"})
    url = f"https://api.gdeltproject.org/api/v2/doc/doc?{params}"
    try:
        with urlopen(Request(url, headers={"User-Agent": "Muklanovich-Research/0.1 (discovery metadata only)"}), timeout=30) as response:
            payload = json.loads(response.read())
    except HTTPError as error:
        if error.code == 429:
            raise RuntimeError("GDELT public-endpoint rate limit (HTTP 429); no data was imported and the next scheduled run should retry.") from error
        raise
    return payload.get("articles", []) if isinstance(payload, dict) else []


def occurred_at(value: object) -> datetime:
    if isinstance(value, str):
        try:
            return datetime.strptime(value, "%Y%m%dT%H%M%SZ").replace(tzinfo=UTC)
        except ValueError:
            pass
    return datetime.now(UTC)


def run(database_url: str, hours: int, limit: int, theme: str) -> None:
    if theme not in QUERIES:
        raise ValueError(f"Unknown theme: {theme}. Choose one of: {', '.join(QUERIES)}")
    with psycopg.connect(database_url) as connection:
        with connection.cursor() as cursor:
            cursor.execute("select id::text from sources where slug = 'gdelt-discovery'")
            row = cursor.fetchone()
            if not row:
                raise RuntimeError("Apply database/migrations/013_news_source_expansion.sql first.")
            source_id = row[0]
            cursor.execute("insert into ingestion_runs (source_id, status) values (%s, 'started') returning id", (source_id,))
            run_id = cursor.fetchone()[0]
        connection.commit()
        written = 0
        read = 0
        try:
            for article in fetch(QUERIES[theme], hours, limit):
                read += 1
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
            with connection.cursor() as cursor:
                cursor.execute("update ingestion_runs set status = 'completed', completed_at = now(), records_read = %s, records_written = %s where id = %s", (read, written, run_id))
            connection.commit()
        except Exception as error:
            connection.rollback()
            with connection.cursor() as cursor:
                cursor.execute("update ingestion_runs set status = 'failed', completed_at = now(), error_message = %s where id = %s", (str(error), run_id))
            connection.commit()
            raise
    print(f"Imported {written} GDELT discovery records ({theme}, last {hours} hours)")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--hours", type=int, default=24, help="Lookback window in hours; default: 24")
    parser.add_argument("--limit", type=int, default=25, help="Maximum GDELT records per request; default: 25")
    parser.add_argument("--theme", choices=sorted(QUERIES), default="global-macro-risk", help="One theme per run to respect public rate limits")
    args = parser.parse_args()
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        sys.exit("DATABASE_URL must be set. See ingestion/.env.example.")
    run(database_url, args.hours, args.limit, args.theme)
