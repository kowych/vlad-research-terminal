"""Ingest Bank of England MPC decision dates from the official schedule.

The schedule confirms dates but does not publish a release time for every
future meeting. Events are therefore stored as ``date_only`` and the UI shows
``TIME TBC`` until the Bank of England publishes a precise timestamp.
"""

from __future__ import annotations

import html
import json
import os
import re
import sys
from datetime import UTC, date, datetime, time
from urllib.request import Request, urlopen

import psycopg

SCHEDULE_URL = "https://www.bankofengland.co.uk/monetary-policy/upcoming-mpc-dates"
MONTHS = {
    name: number
    for number, name in enumerate(
        (
            "January", "February", "March", "April", "May", "June",
            "July", "August", "September", "October", "November", "December",
        ),
        start=1,
    )
}


def fetch_schedule() -> str:
    request = Request(
        SCHEDULE_URL,
        headers={"User-Agent": "Muklanovich-Research/0.1 (official calendar ingestion)"},
    )
    with urlopen(request, timeout=30) as response:
        return response.read().decode("utf-8")


def text_content(value: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html.unescape(value))).strip()


def decision_dates(page: str, today: date) -> list[dict[str, str]]:
    events: list[dict[str, str]] = []
    sections = re.finditer(
        r"<h2>\s*(\d{4})\s+(confirmed|provisional)\s+dates\s*</h2>\s*<table.*?>(.*?)</table>",
        page,
        re.IGNORECASE | re.DOTALL,
    )

    for section in sections:
        year = int(section.group(1))
        schedule_status = section.group(2).lower()
        for row in re.findall(r"<tr[^>]*>\s*<td[^>]*>(.*?)</td>\s*<td[^>]*>(.*?)</td>\s*</tr>", section.group(3), re.IGNORECASE | re.DOTALL):
            match = re.search(r"(?:Monday|Tuesday|Wednesday|Thursday|Friday)\s+(\d{1,2})\s+([A-Za-z]+)", text_content(row[0]))
            if not match or match.group(2) not in MONTHS:
                continue
            event_date = date(year, MONTHS[match.group(2)], int(match.group(1)))
            if event_date < today:
                continue
            events.append({"date": event_date.isoformat(), "schedule_status": schedule_status, "description": text_content(row[1])})

    return events


def run(database_url: str) -> None:
    today = datetime.now(UTC).date()
    schedule = fetch_schedule()
    events = decision_dates(schedule, today)
    if not events:
        raise RuntimeError("No upcoming Bank of England MPC dates found in the official schedule.")

    with psycopg.connect(database_url) as connection:
        with connection.cursor() as cursor:
            cursor.execute("select id::text from sources where slug = 'bank-of-england'")
            source = cursor.fetchone()
            cursor.execute("select id::text from countries where iso2 = 'GB'")
            country = cursor.fetchone()
            if not source or not country:
                raise RuntimeError("Apply the base schema and seed data before running this worker.")
            source_id, country_id = source[0], country[0]
            cursor.execute("insert into ingestion_runs (source_id, status) values (%s, 'started') returning id", (source_id,))
            run_id = cursor.fetchone()[0]
        connection.commit()

        try:
            with connection.cursor() as cursor:
                for event in events:
                    event_date = date.fromisoformat(event["date"])
                    external_id = f"boe-mpc-decision:{event_date.isoformat()}"
                    cursor.execute(
                        """
                        insert into economic_calendar_events (
                          source_id, country_id, external_id, title, category,
                          scheduled_at, timing_precision, reference_period,
                          importance, currency_code, source_name, source_url,
                          original_url, status, last_updated_at, raw_payload
                        ) values (
                          %s, %s, %s, 'Bank Rate Decision & MPC Summary', 'Monetary Policy',
                          %s, 'date_only', %s, 5, 'GBP', 'Bank of England', %s,
                          %s, 'scheduled', now(), %s::jsonb
                        ) on conflict (source_id, external_id) do update set
                          scheduled_at = excluded.scheduled_at,
                          timing_precision = excluded.timing_precision,
                          reference_period = excluded.reference_period,
                          source_url = excluded.source_url,
                          original_url = excluded.original_url,
                          status = excluded.status,
                          last_updated_at = now(),
                          raw_payload = excluded.raw_payload,
                          ingested_at = now()
                        """,
                        (
                            source_id,
                            country_id,
                            external_id,
                            datetime.combine(event_date, time(12, 0), tzinfo=UTC),
                            event["schedule_status"],
                            SCHEDULE_URL,
                            SCHEDULE_URL,
                            json.dumps(event),
                        ),
                    )

                expected_ids = [f"boe-mpc-decision:{event['date']}" for event in events]
                cursor.execute(
                    """
                    delete from economic_calendar_events
                    where source_id = %s
                      and external_id like 'boe-mpc-decision:%%'
                      and not (external_id = any(%s))
                    """,
                    (source_id, expected_ids),
                )
                cursor.execute(
                    """
                    update ingestion_runs
                    set status = 'completed', completed_at = now(), records_read = %s, records_written = %s
                    where id = %s
                    """,
                    (len(events), len(events), run_id),
                )
            connection.commit()
        except Exception as error:
            connection.rollback()
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    update ingestion_runs
                    set status = 'failed', completed_at = now(), error_message = %s
                    where id = %s
                    """,
                    (str(error), run_id),
                )
            connection.commit()
            raise

    print(f"Upserted {len(events)} upcoming Bank of England MPC dates")


if __name__ == "__main__":
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        sys.exit("DATABASE_URL must be set. See ingestion/.env.example.")
    run(database_url)
