"""Ingest an authorised Trading Economics economic-calendar window.

Requires ``TRADING_ECONOMICS_API_KEY``. It is not a Forex Factory fallback:
that site's terms prohibit redistribution of calendar data. The connector keeps
the provider record plus the linked official source for provenance.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import UTC, datetime, timedelta
from decimal import Decimal, InvalidOperation
from urllib.parse import quote
from urllib.request import Request, urlopen

import psycopg

TE_COUNTRIES = {"US": "united states", "IR": "iran", "GB": "united kingdom", "FR": "france", "DE": "germany", "UA": "ukraine", "RU": "russia", "AU": "australia", "CA": "canada", "NZ": "new zealand", "CN": "china", "JP": "japan", "IT": "italy", "ES": "spain", "CH": "switzerland", "NO": "norway", "SE": "sweden", "TR": "turkey", "IN": "india", "KR": "south korea", "PL": "poland"}


def numeric(value: object) -> Decimal | None:
    if value in (None, ""):
        return None
    try:
        return Decimal(str(value).replace(",", ""))
    except InvalidOperation:
        return None


def parse_time(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)


def fetch(country: str, start: str, end: str, api_key: str) -> list[dict[str, object]]:
    url = f"https://api.tradingeconomics.com/calendar/country/{quote(country, safe='')}/{start}/{end}?c={quote(api_key, safe='')}"
    with urlopen(Request(url, headers={"User-Agent": "Muklanovich-Research/0.1 (licensed calendar ingestion)"}), timeout=30) as response:
        payload = json.loads(response.read())
    if not isinstance(payload, list):
        raise RuntimeError(f"Unexpected calendar response for {country}")
    return payload


def run(database_url: str, api_key: str, days: int) -> None:
    start = datetime.now(UTC).date()
    end = start + timedelta(days=days)
    with psycopg.connect(database_url) as connection:
        with connection.cursor() as cursor:
            cursor.execute("select id::text from sources where slug = 'trading-economics-calendar'")
            row = cursor.fetchone()
            if not row:
                raise RuntimeError("Apply database/migrations/012_economic_calendar.sql first.")
            source_id = row[0]
            cursor.execute("select iso2, id::text from countries")
            country_ids = dict(cursor.fetchall())
        written = 0
        for iso2, provider_country in TE_COUNTRIES.items():
            for event in fetch(provider_country, start.isoformat(), end.isoformat(), api_key):
                external_id, scheduled_at, title = event.get("CalendarId") or event.get("CalendarID"), event.get("Date"), event.get("Event")
                if not external_id or not scheduled_at or not title:
                    continue
                actual = event.get("Actual")
                status = "released" if actual not in (None, "") else "scheduled"
                timing = "estimated" if str(event.get("DateSpan", "0")) == "1" else "exact"
                importance = min(5, max(1, int(event.get("Importance") or 1)))
                with connection.cursor() as cursor:
                    cursor.execute("""
                      insert into economic_calendar_events (source_id, country_id, external_id, title, category, scheduled_at, timing_precision, reference_period, importance, currency_code, forecast_text, previous_text, actual_text, forecast_value, previous_value, actual_value, source_name, source_url, original_url, status, last_updated_at, raw_payload)
                      values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb)
                      on conflict (source_id, external_id) do update set scheduled_at = excluded.scheduled_at, timing_precision = excluded.timing_precision, reference_period = excluded.reference_period, importance = excluded.importance, forecast_text = excluded.forecast_text, previous_text = excluded.previous_text, actual_text = excluded.actual_text, forecast_value = excluded.forecast_value, previous_value = excluded.previous_value, actual_value = excluded.actual_value, status = excluded.status, last_updated_at = excluded.last_updated_at, raw_payload = excluded.raw_payload, ingested_at = now()
                    """, (source_id, country_ids.get(iso2), str(external_id), str(title), event.get("Category"), parse_time(str(scheduled_at)), timing, event.get("Reference"), importance, event.get("Currency"), event.get("Forecast"), event.get("Previous"), actual, numeric(event.get("ForecastValue")), numeric(event.get("PreviousValue")), numeric(event.get("ActualValue")), event.get("Source"), event.get("SourceURL"), event.get("URL"), status, parse_time(str(event["LastUpdate"])) if event.get("LastUpdate") else None, json.dumps(event)))
                    written += 1
            connection.commit()
    print(f"Upserted {written} calendar events from {start.isoformat()} to {end.isoformat()}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--days", type=int, default=14, help="Forward window in days; default: 14")
    args = parser.parse_args()
    database_url = os.environ.get("DATABASE_URL")
    api_key = os.environ.get("TRADING_ECONOMICS_API_KEY")
    if not database_url or not api_key:
        sys.exit("DATABASE_URL and TRADING_ECONOMICS_API_KEY must be set. See ingestion/.env.example.")
    run(database_url, api_key, args.days)
