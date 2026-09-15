"""Ingest the free BusinessQuant US economic-release calendar.

The provider returns release dates but not release times or consensus. Records
are therefore stored as date-only at a neutral UTC placeholder, never as an
exact release timestamp, and remain separate from published news evidence.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import UTC, date, datetime, time, timedelta
from decimal import Decimal, InvalidOperation
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import psycopg

SOURCE_URL = "https://businessquant.com/docs/api/economic-calendar"


def numeric(value: object) -> Decimal | None:
    if value in (None, ""):
        return None
    try:
        return Decimal(str(value).replace(",", ""))
    except InvalidOperation:
        return None


def importance(item: dict[str, object]) -> int:
    name = str(item.get("name", "")).lower()
    category = str(item.get("category", "")).lower()
    if any(term in name for term in ("consumer price", "nonfarm", "unemployment rate", "gross domestic product", "federal funds")):
        return 5
    if category in {"inflation", "employment", "gdp", "output"}:
        return 4
    if category in {"rates", "trade", "credit", "housing", "business"}:
        return 3
    return 2


def fetch(api_key: str, start: date, end: date) -> list[dict[str, object]]:
    query = urlencode({"from_date": start.isoformat(), "till_date": end.isoformat(), "api_key": api_key})
    request = Request(f"https://data.businessquant.com/calendar/economic?{query}", headers={"User-Agent": "Muklanovich-Research/0.1 (calendar metadata ingestion)"})
    with urlopen(request, timeout=30) as response:
        payload = json.loads(response.read())
    if not isinstance(payload, dict) or not isinstance(payload.get("data"), list):
        raise RuntimeError("Unexpected BusinessQuant calendar response")
    return [item for item in payload["data"] if isinstance(item, dict)]


def run(database_url: str, api_key: str, days: int) -> None:
    start = datetime.now(UTC).date()
    end = start + timedelta(days=days)
    rows = fetch(api_key, start, end)
    with psycopg.connect(database_url) as connection:
        with connection.cursor() as cursor:
            cursor.execute("select id::text from sources where slug = 'businessquant-us-calendar'")
            source = cursor.fetchone()
            if not source:
                raise RuntimeError("Apply database/migrations/019_businessquant_us_calendar.sql first.")
            cursor.execute("select id::text from countries where iso2 = 'US'")
            country = cursor.fetchone()
            if not country:
                raise RuntimeError("United States country record is missing.")
            source_id, country_id = source[0], country[0]
            cursor.execute("insert into ingestion_runs (source_id, status) values (%s, 'started') returning id", (source_id,))
            run_id = cursor.fetchone()[0]
        connection.commit()
        written = 0
        try:
            with connection.cursor() as cursor:
                for item in rows:
                    release = item.get("next_release")
                    indicator_id = item.get("indicator_id")
                    title = item.get("name")
                    if not isinstance(release, str) or not indicator_id or not isinstance(title, str):
                        continue
                    release_date = date.fromisoformat(release)
                    scheduled_at = datetime.combine(release_date, time(12, 0), tzinfo=UTC)
                    external_id = f"{indicator_id}:{release}"
                    cursor.execute("""
                      insert into economic_calendar_events (source_id, country_id, external_id, title, category, scheduled_at, timing_precision, reference_period, importance, currency_code, previous_text, previous_value, source_name, source_url, original_url, status, last_updated_at, raw_payload)
                      values (%s, %s, %s, %s, %s, %s, 'date_only', %s, %s, 'USD', %s, %s, %s, %s, %s, 'scheduled', now(), %s::jsonb)
                      on conflict (source_id, external_id) do update set
                        title = excluded.title, category = excluded.category, scheduled_at = excluded.scheduled_at,
                        importance = excluded.importance, previous_text = excluded.previous_text,
                        previous_value = excluded.previous_value, last_updated_at = now(),
                        raw_payload = excluded.raw_payload, ingested_at = now()
                    """, (source_id, country_id, external_id, title, item.get("category"), scheduled_at, item.get("latest_date"), importance(item), str(item.get("prior_value")) if item.get("prior_value") is not None else None, numeric(item.get("prior_value")), "BusinessQuant", SOURCE_URL, SOURCE_URL, json.dumps(item)))
                    written += 1
                cursor.execute("update ingestion_runs set status = 'completed', completed_at = now(), records_read = %s, records_written = %s where id = %s", (len(rows), written, run_id))
            connection.commit()
        except Exception as error:
            connection.rollback()
            with connection.cursor() as cursor:
                cursor.execute("update ingestion_runs set status = 'failed', completed_at = now(), error_message = %s where id = %s", (str(error), run_id))
            connection.commit()
            raise
    print(f"Upserted {written} US calendar releases from {start.isoformat()} to {end.isoformat()}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--days", type=int, default=14, help="Forward window in days; default: 14")
    args = parser.parse_args()
    database_url = os.environ.get("DATABASE_URL")
    api_key = os.environ.get("BUSINESSQUANT_API_KEY")
    if not database_url or not api_key:
        sys.exit("DATABASE_URL and BUSINESSQUANT_API_KEY must be set. See ingestion/.env.example.")
    run(database_url, api_key, args.days)
