"""Ingest upcoming FOMC policy-decision dates from the official Fed schedule."""

from __future__ import annotations

import html
import json
import os
import re
import sys
from datetime import UTC, date, datetime, time
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo

import psycopg

SCHEDULE_URL = "https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm"
MONTHS = {name: index for index, name in enumerate(("January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"), start=1)}


def fetch_schedule() -> str:
    with urlopen(Request(SCHEDULE_URL, headers={"User-Agent": "Muklanovich-Research/0.1 (official calendar ingestion)"}), timeout=30) as response:
        return html.unescape(re.sub(r"<[^>]+>", " ", response.read().decode("utf-8")))


def meetings(text: str, year: int) -> list[date]:
    match = re.search(rf"{year} FOMC Meetings\s+(.*?)(?=\d{{4}} FOMC Meetings|$)", text, re.DOTALL)
    if not match:
        return []
    section = match.group(1).split("Note:", 1)[0]
    return [date(year, MONTHS[month], int(end_day)) for month, _start_day, end_day in re.findall(r"(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{1,2})-(\d{1,2})\*?", section)]


def run(database_url: str) -> None:
    today = datetime.now(UTC).date()
    schedule = fetch_schedule()
    decision_dates = [item for year in (today.year, today.year + 1) for item in meetings(schedule, year) if item >= today]
    if not decision_dates:
        raise RuntimeError("No upcoming FOMC meetings found in the official schedule.")
    eastern = ZoneInfo("America/New_York")
    with psycopg.connect(database_url) as connection:
        with connection.cursor() as cursor:
            cursor.execute("select id::text from sources where slug = 'federal-reserve-fomc-calendar'")
            source = cursor.fetchone()
            cursor.execute("select id::text from countries where iso2 = 'US'")
            country = cursor.fetchone()
            if not source or not country:
                raise RuntimeError("Apply database/migrations/020_fomc_calendar.sql and seed countries first.")
            source_id, country_id = source[0], country[0]
            cursor.execute("insert into ingestion_runs (source_id, status) values (%s, 'started') returning id", (source_id,))
            run_id = cursor.fetchone()[0]
        connection.commit()
        try:
            with connection.cursor() as cursor:
                for decision_date in decision_dates:
                    scheduled_at = datetime.combine(decision_date, time(14, 0), eastern).astimezone(UTC)
                    cursor.execute("""
                      insert into economic_calendar_events (source_id, country_id, external_id, title, category, scheduled_at, timing_precision, importance, currency_code, source_name, source_url, original_url, status, last_updated_at, raw_payload)
                      values (%s, %s, %s, 'FOMC Policy Decision', 'Monetary Policy', %s, 'estimated', 5, 'USD', 'Federal Reserve', %s, %s, 'scheduled', now(), %s::jsonb)
                      on conflict (source_id, external_id) do update set scheduled_at = excluded.scheduled_at, last_updated_at = now(), raw_payload = excluded.raw_payload, ingested_at = now()
                    """, (source_id, country_id, f"fomc-policy-decision:{decision_date.isoformat()}", scheduled_at, SCHEDULE_URL, SCHEDULE_URL, json.dumps({"meeting_end_date": decision_date.isoformat(), "scheduled_policy_statement_et": "14:00", "schedule_url": SCHEDULE_URL})))
                expected_ids = [f"fomc-policy-decision:{decision_date.isoformat()}" for decision_date in decision_dates]
                cursor.execute("delete from economic_calendar_events where source_id = %s and external_id like 'fomc-policy-decision:%%' and not (external_id = any(%s))", (source_id, expected_ids))
                cursor.execute("update ingestion_runs set status = 'completed', completed_at = now(), records_read = %s, records_written = %s where id = %s", (len(decision_dates), len(decision_dates), run_id))
            connection.commit()
        except Exception as error:
            connection.rollback()
            with connection.cursor() as cursor:
                cursor.execute("update ingestion_runs set status = 'failed', completed_at = now(), error_message = %s where id = %s", (str(error), run_id))
            connection.commit()
            raise
    print(f"Upserted {len(decision_dates)} upcoming FOMC policy decisions")


if __name__ == "__main__":
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        sys.exit("DATABASE_URL must be set. See ingestion/.env.example.")
    run(database_url)
