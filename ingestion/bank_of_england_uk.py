"""Ingest the official Bank Rate history for the United Kingdom macro desk."""

from __future__ import annotations

import argparse
import csv
import io
import json
import os
import sys
from datetime import date, datetime
from decimal import Decimal
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import psycopg

BOE_DATA_URL = "https://www.bankofengland.co.uk/boeapps/database/_iadb-fromshowcolumns.asp"
SERIES = {
    "indicator_slug": "policy-rate",
    "code": "IUDBEDR",
    "display_name": "Bank Rate",
    "unit": "percent per annum",
}


def fetch(start: str, end: str) -> list[dict[str, str]]:
    query = urlencode({
        "csv.x": "yes",
        "Datefrom": start,
        "Dateto": end,
        "SeriesCodes": SERIES["code"],
        "UsingCodes": "Y",
        "CSVF": "TN",
        "VPD": "Y",
    })
    request = Request(f"{BOE_DATA_URL}?{query}", headers={"User-Agent": "Muklanovich-Research/0.1 (local macro research)"})
    with urlopen(request, timeout=30) as response:
        rows = list(csv.DictReader(io.TextIOWrapper(response, encoding="utf-8-sig")))
    if not rows or "DATE" not in rows[0] or SERIES["code"] not in rows[0]:
        raise RuntimeError("Unexpected Bank of England CSV response")
    return rows


def run(database_url: str, start: str, end: str) -> None:
    rows = fetch(start, end)
    vintage = date.today().isoformat()
    observations = [
        (datetime.strptime(row["DATE"], "%d %b %Y").date().isoformat(), row[SERIES["code"]])
        for row in rows if row[SERIES["code"]].strip()
    ]
    with psycopg.connect(database_url) as connection:
        with connection.cursor() as cursor:
            cursor.execute("insert into ingestion_runs (source_id, status) select id, 'started' from sources where slug = 'bank-of-england' returning id")
            run_id = cursor.fetchone()[0]
            cursor.execute("""
              insert into source_series (source_id, indicator_id, country_id, external_id, display_name, unit)
              select sources.id, indicators.id, countries.id, %s, %s, %s from sources, indicators, countries
              where sources.slug = 'bank-of-england' and indicators.slug = %s and countries.iso2 = 'GB'
              on conflict (source_id, country_id, external_id) do update set display_name = excluded.display_name, unit = excluded.unit
              returning id
            """, (SERIES["code"], SERIES["display_name"], SERIES["unit"], SERIES["indicator_slug"]))
            source_series_id = cursor.fetchone()[0]
        connection.commit()
        try:
            inserted = 0
            with connection.cursor() as cursor:
                for period_start, value in observations:
                    raw_observation = {"series_code": SERIES["code"], "period_start": period_start, "value": value, "retrieved_on": vintage}
                    cursor.execute("""
                      insert into observations (source_series_id, period_start, value, as_of_date, raw_payload)
                      values (%s, %s, %s, %s, %s::jsonb)
                      on conflict (source_series_id, period_start, as_of_date) do nothing
                    """, (source_series_id, period_start, Decimal(value), vintage, json.dumps(raw_observation)))
                    inserted += cursor.rowcount
                cursor.execute("update ingestion_runs set status = 'completed', completed_at = now(), records_read = %s, records_written = %s where id = %s", (len(observations), inserted, run_id))
            connection.commit()
            print(f"{SERIES['code']}: {inserted} new observations; official database retrieved {vintage}")
        except Exception as error:
            connection.rollback()
            with connection.cursor() as cursor:
                cursor.execute("update ingestion_runs set status = 'failed', completed_at = now(), error_message = %s where id = %s", (str(error), run_id))
            connection.commit()
            raise


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--start", default="01/Jan/1990", help="Earliest date, e.g. 01/Jan/1990")
    parser.add_argument("--end", default="now", help='Latest date, or "now"')
    args = parser.parse_args()
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        sys.exit("DATABASE_URL must be set. See ingestion/.env.example.")
    run(database_url, args.start, args.end)


if __name__ == "__main__":
    main()
