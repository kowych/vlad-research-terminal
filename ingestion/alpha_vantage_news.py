"""Ingest Alpha Vantage market-news metadata without fetching publisher pages.

The provider's topical query is intentionally broad so one free-tier request
captures cross-border macro, energy and technology events.  The classifier
links those items into the country and market event graph afterwards.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from datetime import UTC, datetime, timedelta
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import psycopg

TOPICS = "economy_macro,economy_monetary,economy_fiscal,energy_transportation,technology"


def parse_time(value: object) -> datetime:
    if isinstance(value, str):
        for pattern in ("%Y%m%dT%H%M%S", "%Y%m%dT%H%M"):
            try:
                return datetime.strptime(value, pattern).replace(tzinfo=UTC)
            except ValueError:
                pass
    return datetime.now(UTC)


def fetch(api_key: str, limit: int, hours: int) -> list[dict[str, object]]:
    since = (datetime.now(UTC) - timedelta(hours=hours)).strftime("%Y%m%dT%H%M")
    query = urlencode({"function": "NEWS_SENTIMENT", "topics": TOPICS, "time_from": since, "sort": "LATEST", "limit": limit, "apikey": api_key})
    request = Request(f"https://www.alphavantage.co/query?{query}", headers={"User-Agent": "Muklanovich-Research/0.1 (local metadata ingestion)"})
    with urlopen(request, timeout=30) as response:
        payload = json.loads(response.read())
    if not isinstance(payload, dict):
        raise RuntimeError("Unexpected Alpha Vantage response")
    message = payload.get("Information") or payload.get("Note") or payload.get("Error Message")
    if message:
        raise RuntimeError(f"Alpha Vantage: {message}")
    feed = payload.get("feed", [])
    if not isinstance(feed, list):
        raise RuntimeError("Alpha Vantage response did not contain a news feed")
    return [item for item in feed if isinstance(item, dict)]


def run(database_url: str, api_key: str, limit: int, hours: int) -> None:
    with psycopg.connect(database_url) as connection:
        with connection.cursor() as cursor:
            cursor.execute("select id::text from sources where slug = 'alpha-vantage-market-news'")
            row = cursor.fetchone()
            if not row:
                raise RuntimeError("Apply database/migrations/015_alpha_vantage_market_news.sql first.")
            source_id = row[0]
            cursor.execute("insert into ingestion_runs (source_id, status) values (%s, 'started') returning id", (source_id,))
            run_id = cursor.fetchone()[0]
        connection.commit()
        try:
            feed = fetch(api_key, limit, hours)
            written = 0
            with connection.cursor() as cursor:
                for item in feed:
                    url, title = item.get("url"), item.get("title")
                    if not isinstance(url, str) or not isinstance(title, str):
                        continue
                    canonical_url = url.split("#", 1)[0]
                    external_id = hashlib.sha256(canonical_url.encode()).hexdigest()
                    summary = item.get("summary") if isinstance(item.get("summary"), str) else None
                    published = parse_time(item.get("time_published"))
                    cursor.execute("""
                      insert into raw_documents (source_id, external_id, original_url, canonical_url, title_raw, summary_raw, language_code, source_published_at, content_hash, raw_payload)
                      values (%s, %s, %s, %s, %s, %s, 'en', %s, %s, %s::jsonb)
                      on conflict (canonical_url) do nothing returning id
                    """, (source_id, external_id, url, canonical_url, title, summary, published, external_id, json.dumps(item)))
                    raw = cursor.fetchone()
                    if not raw:
                        continue
                    cursor.execute("insert into news_articles (raw_document_id, headline, summary, language_code, published_at) values (%s, %s, %s, 'en', %s)", (raw[0], title, summary, published))
                    written += 1
                cursor.execute("update ingestion_runs set status = 'completed', completed_at = now(), records_read = %s, records_written = %s where id = %s", (len(feed), written, run_id))
            connection.commit()
        except Exception as error:
            connection.rollback()
            with connection.cursor() as cursor:
                cursor.execute("update ingestion_runs set status = 'failed', completed_at = now(), error_message = %s where id = %s", (str(error), run_id))
            connection.commit()
            raise
    print(f"Imported {written} Alpha Vantage market-news metadata records")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--limit", type=int, default=50, help="Maximum provider records; default: 50")
    parser.add_argument("--hours", type=int, default=168, help="Freshness window in hours; default: 168 (7 days)")
    args = parser.parse_args()
    database_url = os.environ.get("DATABASE_URL")
    api_key = os.environ.get("ALPHA_VANTAGE_API_KEY") or os.environ.get("ALPHA_API_KEY")
    if not database_url or not api_key:
        sys.exit("DATABASE_URL and ALPHA_VANTAGE_API_KEY must be set. See ingestion/.env.example.")
    run(database_url, api_key, args.limit, args.hours)
