"""Ingest official BOJ, RBA and RBNZ forward monetary-policy calendars.

The BOJ and RBA schedules are fetched from their primary websites on every
run. RBNZ's public schedule currently returns HTTP 403 to server-to-server
clients, so its dates are a clearly marked official snapshot captured from the
published schedule. Do not fabricate release times for any of the three.
"""

from __future__ import annotations

import html
import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass
from datetime import UTC, date, datetime, time
import psycopg

BOJ_SCHEDULE_URL = "https://www.boj.or.jp/en/mopo/mpmsche_minu/index.htm"
RBA_SCHEDULE_URL = "https://www.rba.gov.au/schedules-events/board-meeting-schedules.html"
RBNZ_SCHEDULE_URL = "https://www.rbnz.govt.nz/news-and-events/how-we-release-information/ocr-decision-dates-and-financial-stability-report-dates-to-feb-2028"

MONTHS = {
    "jan": 1, "january": 1, "feb": 2, "february": 2, "mar": 3, "march": 3,
    "apr": 4, "april": 4, "may": 5, "jun": 6, "june": 6, "jul": 7,
    "july": 7, "aug": 8, "august": 8, "sep": 9, "sept": 9, "september": 9,
    "oct": 10, "october": 10, "nov": 11, "november": 11, "dec": 12, "december": 12,
}

# RBNZ's page is public and official but currently blocks automated server
# requests (HTTP 403). These dates are a provenance-labelled bootstrap from the
# page published on 19 February 2026, not an inferred recurring schedule.
RBNZ_OFFICIAL_SNAPSHOT = (
    ("2026-10-28", "RBNZ Monetary Policy Review & OCR"),
    ("2026-12-09", "RBNZ Monetary Policy Statement & OCR"),
    ("2027-02-10", "RBNZ Monetary Policy Review & OCR"),
    ("2027-03-17", "RBNZ Monetary Policy Statement & OCR"),
    ("2027-05-05", "RBNZ Monetary Policy Review & OCR"),
    ("2027-06-16", "RBNZ Monetary Policy Statement & OCR"),
    ("2027-08-04", "RBNZ Monetary Policy Review & OCR"),
    ("2027-09-15", "RBNZ Monetary Policy Statement & OCR"),
    ("2027-10-27", "RBNZ Monetary Policy Review & OCR"),
    ("2027-12-08", "RBNZ Monetary Policy Statement & OCR"),
    ("2028-02-09", "RBNZ Monetary Policy Review & OCR"),
)


@dataclass(frozen=True)
class PolicyEvent:
    source_slug: str
    source_name: str
    country_iso2: str
    currency: str
    external_id: str
    title: str
    event_date: date
    source_url: str
    raw_payload: dict[str, object]


def fetch_page(url: str) -> str:
    # Both official pages are public, but their web application firewalls
    # reject Python's default TLS client. macOS and standard Linux runtimes
    # ship curl; use it transparently rather than impersonating a browser.
    result = subprocess.run(
        ["curl", "--fail", "--location", "--silent", "--show-error", "--max-time", "30", url],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout


def text_content(value: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html.unescape(value))).strip()


def parse_boj_meeting_date(value: str, year: int) -> date | None:
    match = re.search(r"\b([A-Za-z]+)\.?\s+(\d{1,2})\b", value)
    if not match:
        return None
    month = MONTHS.get(match.group(1).lower().rstrip("."))
    if not month:
        return None
    end_day = re.search(r",\s*(\d{1,2})\s*\([^)]+\)", value[match.end():])
    return date(year, month, int(end_day.group(1) if end_day else match.group(2)))


def boj_events(page: str, today: date) -> list[PolicyEvent]:
    events: list[PolicyEvent] = []
    sections = re.finditer(r"<h2[^>]*>\s*(\d{4})\s*</h2>(.*?)(?=<h2[^>]*>|$)", page, re.IGNORECASE | re.DOTALL)
    for section in sections:
        year = int(section.group(1))
        for row in re.findall(r"<tr\b[^>]*>(.*?)</tr>", section.group(2), re.IGNORECASE | re.DOTALL):
            cells = re.findall(r"<t[dh]\b[^>]*>(.*?)</t[dh]>", row, re.IGNORECASE | re.DOTALL)
            if not cells:
                continue
            meeting_text = text_content(cells[0])
            event_date = parse_boj_meeting_date(meeting_text, year)
            if not event_date or event_date < today:
                continue
            events.append(PolicyEvent(
                source_slug="bank-of-japan-policy-calendar",
                source_name="Bank of Japan",
                country_iso2="JP",
                currency="JPY",
                external_id=f"boj-policy-decision:{event_date.isoformat()}",
                title="BOJ Monetary Policy Decision",
                event_date=event_date,
                source_url=BOJ_SCHEDULE_URL,
                raw_payload={"meeting_dates": meeting_text, "schedule_url": BOJ_SCHEDULE_URL},
            ))
    return events


def rba_events(page: str, today: date) -> list[PolicyEvent]:
    events: list[PolicyEvent] = []
    sections = re.finditer(
        r"<caption[^>]*>\s*Board meeting schedules\s+(\d{4})\s*</caption>(.*?)</table>",
        page,
        re.IGNORECASE | re.DOTALL,
    )
    for section in sections:
        year = int(section.group(1))
        for row in re.findall(r"<tr\b[^>]*>(.*?)</tr>", section.group(2), re.IGNORECASE | re.DOTALL):
            cells = [text_content(cell) for cell in re.findall(r"<t[dh]\b[^>]*>(.*?)</t[dh]>", row, re.IGNORECASE | re.DOTALL)]
            if len(cells) < 2:
                continue
            meeting_text = cells[1]
            match = re.search(r"((?:\d{1,2}\s*[–-]\s*)?\d{1,2})\s+([A-Za-z]+)", meeting_text)
            if not match:
                continue
            month = MONTHS.get(match.group(2).lower())
            days = re.findall(r"\d{1,2}", match.group(1))
            if not month or not days:
                continue
            event_date = date(year, month, int(days[-1]))
            if event_date < today:
                continue
            events.append(PolicyEvent(
                source_slug="reserve-bank-australia-policy-calendar",
                source_name="Reserve Bank of Australia",
                country_iso2="AU",
                currency="AUD",
                external_id=f"rba-policy-decision:{event_date.isoformat()}",
                title="RBA Monetary Policy Board Decision",
                event_date=event_date,
                source_url=RBA_SCHEDULE_URL,
                raw_payload={"meeting_dates": meeting_text, "schedule_url": RBA_SCHEDULE_URL},
            ))
    return events


def rbnz_events(today: date) -> list[PolicyEvent]:
    return [
        PolicyEvent(
            source_slug="reserve-bank-new-zealand-policy-calendar",
            source_name="Reserve Bank of New Zealand",
            country_iso2="NZ",
            currency="NZD",
            external_id=f"rbnz-ocr-decision:{date_text}",
            title=title,
            event_date=event_date,
            source_url=RBNZ_SCHEDULE_URL,
            raw_payload={
                "date": date_text,
                "announcement": title,
                "schedule_url": RBNZ_SCHEDULE_URL,
                "schedule_published": "2026-02-19",
                "source_mode": "official_schedule_snapshot",
            },
        )
        for date_text, title in RBNZ_OFFICIAL_SNAPSHOT
        if (event_date := date.fromisoformat(date_text)) >= today
    ]


def upsert_events(database_url: str, source_slug: str, events: list[PolicyEvent]) -> int:
    if not events:
        raise RuntimeError(f"No upcoming events parsed for {source_slug}.")
    with psycopg.connect(database_url) as connection:
        with connection.cursor() as cursor:
            cursor.execute("select id::text from sources where slug = %s", (source_slug,))
            source = cursor.fetchone()
            cursor.execute("select iso2, id::text from countries where iso2 = any(%s)", ([event.country_iso2 for event in events],))
            countries = dict(cursor.fetchall())
            if not source or len(countries) != len({event.country_iso2 for event in events}):
                raise RuntimeError("Apply database/migrations/021_asia_pacific_policy_calendars.sql and seed countries first.")
            source_id = source[0]
            cursor.execute("insert into ingestion_runs (source_id, status) values (%s, 'started') returning id", (source_id,))
            run_id = cursor.fetchone()[0]
        connection.commit()

        try:
            with connection.cursor() as cursor:
                for event in events:
                    cursor.execute(
                        """
                        insert into economic_calendar_events (
                          source_id, country_id, external_id, title, category,
                          scheduled_at, timing_precision, importance, currency_code,
                          source_name, source_url, original_url, status,
                          last_updated_at, raw_payload
                        ) values (
                          %s, %s, %s, %s, 'Monetary Policy',
                          %s, 'date_only', 5, %s, %s, %s, %s, 'scheduled',
                          now(), %s::jsonb
                        ) on conflict (source_id, external_id) do update set
                          title = excluded.title,
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
                            countries[event.country_iso2],
                            event.external_id,
                            event.title,
                            datetime.combine(event.event_date, time(12, 0), tzinfo=UTC),
                            event.currency,
                            event.source_name,
                            event.source_url,
                            event.source_url,
                            json.dumps(event.raw_payload),
                        ),
                    )
                cursor.execute(
                    "delete from economic_calendar_events where source_id = %s and not (external_id = any(%s))",
                    (source_id, [event.external_id for event in events]),
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
                    "update ingestion_runs set status = 'failed', completed_at = now(), error_message = %s where id = %s",
                    (str(error), run_id),
                )
            connection.commit()
            raise
    return len(events)


def run(database_url: str) -> None:
    today = datetime.now(UTC).date()
    source_events = {
        "bank-of-japan-policy-calendar": boj_events(fetch_page(BOJ_SCHEDULE_URL), today),
        "reserve-bank-australia-policy-calendar": rba_events(fetch_page(RBA_SCHEDULE_URL), today),
        "reserve-bank-new-zealand-policy-calendar": rbnz_events(today),
    }
    totals = {source_slug: upsert_events(database_url, source_slug, events) for source_slug, events in source_events.items()}
    print("Upserted Asia-Pacific policy events: " + ", ".join(f"{source_slug}={written}" for source_slug, written in totals.items()))


if __name__ == "__main__":
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        sys.exit("DATABASE_URL must be set. See ingestion/.env.example.")
    run(database_url)
