"""Ingest ECB monetary-policy decision dates from the official ECB calendar.

The forward schedule identifies the decision day and press conference but does
not provide a durable timestamp for each future meeting. Every event is stored
as ``date_only`` until a time is published by the ECB.
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

SCHEDULE_URL = "https://www.ecb.europa.eu/press/calendars/mgcgc/html/index.en.html"
EURO_AREA_COUNTRIES = ("FR", "DE", "IT", "ES")


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
    rows = re.findall(r"<dt>\s*(\d{2}/\d{2}/\d{4})\s*</dt>\s*<dd>(.*?)</dd>", page, re.IGNORECASE | re.DOTALL)

    for date_text, description_html in rows:
        description = text_content(description_html)
        if "monetary policy meeting" not in description.lower() or "day 2" not in description.lower():
            continue
        event_date = datetime.strptime(date_text, "%d/%m/%Y").date()
        if event_date >= today:
            events.append({"date": event_date.isoformat(), "description": description})

    return events


def run(database_url: str) -> None:
    today = datetime.now(UTC).date()
    events = decision_dates(fetch_schedule(), today)
    if not events:
        raise RuntimeError("No upcoming ECB monetary policy decision dates found in the official schedule.")

    with psycopg.connect(database_url) as connection:
        with connection.cursor() as cursor:
            cursor.execute("select id::text from sources where slug = 'ecb-communications'")
            source = cursor.fetchone()
            cursor.execute("select iso2, id::text from countries where iso2 = any(%s)", (list(EURO_AREA_COUNTRIES),))
            country_ids = dict(cursor.fetchall())
            if not source or set(country_ids) != set(EURO_AREA_COUNTRIES):
                raise RuntimeError("Apply the base schema and seed data before running this worker.")
            source_id = source[0]
            cursor.execute("insert into ingestion_runs (source_id, status) values (%s, 'started') returning id", (source_id,))
            run_id = cursor.fetchone()[0]
        connection.commit()

        try:
            with connection.cursor() as cursor:
                for event in events:
                    event_date = date.fromisoformat(event["date"])
                    for iso2, country_id in country_ids.items():
                        external_id = f"ecb-policy-decision:{event_date.isoformat()}:{iso2.lower()}"
                        cursor.execute(
                            """
                            insert into economic_calendar_events (
                              source_id, country_id, external_id, title, category,
                              scheduled_at, timing_precision, importance, currency_code,
                              source_name, source_url, original_url, status,
                              last_updated_at, raw_payload
                            ) values (
                              %s, %s, %s, 'ECB Monetary Policy Decision & Press Conference', 'Monetary Policy',
                              %s, 'date_only', 5, 'EUR', 'European Central Bank', %s,
                              %s, 'scheduled', now(), %s::jsonb
                            ) on conflict (source_id, external_id) do update set
                              scheduled_at = excluded.scheduled_at,
                              timing_precision = excluded.timing_precision,
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
                                SCHEDULE_URL,
                                SCHEDULE_URL,
                                json.dumps(event),
                            ),
                        )

                expected_ids = [
                    f"ecb-policy-decision:{event['date']}:{iso2.lower()}"
                    for event in events
                    for iso2 in EURO_AREA_COUNTRIES
                ]
                cursor.execute(
                    """
                    delete from economic_calendar_events
                    where source_id = %s
                      and external_id like 'ecb-policy-decision:%%'
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
                    (len(events), len(events) * len(EURO_AREA_COUNTRIES), run_id),
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

    print(f"Upserted {len(events) * len(EURO_AREA_COUNTRIES)} ECB policy events across {len(EURO_AREA_COUNTRIES)} country desks")


if __name__ == "__main__":
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        sys.exit("DATABASE_URL must be set. See ingestion/.env.example.")
    run(database_url)
