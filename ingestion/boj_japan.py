"""Ingest official Bank of Japan time-series data for the Japan macro desk."""

from __future__ import annotations

import argparse
import gzip
import json
import os
import sys
from datetime import date
from decimal import Decimal
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import psycopg

BOJ_DATA_URL = "https://www.stat-search.boj.or.jp/api/v1/getDataCode"
SERIES = {
    "indicator_slug": "policy-rate",
    "database": "FM01",
    "code": "STRDCLUCON",
    "display_name": "Call Rate, Uncollateralized Overnight, Average",
    "unit": "percent per annum",
}


def fetch(start_month: str, end_month: str) -> dict:
    query = urlencode({"format": "json", "lang": "en", "db": SERIES["database"], "startDate": start_month, "endDate": end_month, "code": SERIES["code"]})
    request = Request(f"{BOJ_DATA_URL}?{query}", headers={"Accept-Encoding": "gzip"})
    with urlopen(request, timeout=30) as response:
        raw = response.read()
        payload = gzip.decompress(raw) if response.headers.get("Content-Encoding") == "gzip" else raw
    data = json.loads(payload)
    if data.get("STATUS") != 200 or not data.get("RESULTSET"):
        raise RuntimeError(f"BOJ request failed: {data.get('MESSAGE', 'empty response')}")
    return data


def iso_date(value: int) -> str:
    text = str(value)
    return f"{text[:4]}-{text[4:6]}-{text[6:8]}"


def run(database_url: str, start_month: str, end_month: str) -> None:
    payload = fetch(start_month, end_month)
    result = payload["RESULTSET"][0]
    as_of_date = iso_date(result["LAST_UPDATE"])
    observations = [(iso_date(day), value) for day, value in zip(result["VALUES"]["SURVEY_DATES"], result["VALUES"]["VALUES"]) if value is not None]
    with psycopg.connect(database_url) as connection:
        with connection.cursor() as cursor:
            cursor.execute("insert into ingestion_runs (source_id, status) select id, 'started' from sources where slug = 'boj' returning id")
            run_id = cursor.fetchone()[0]
            cursor.execute("""
              insert into source_series (source_id, indicator_id, country_id, external_id, display_name, unit)
              select sources.id, indicators.id, countries.id, %s, %s, %s from sources, indicators, countries
              where sources.slug = 'boj' and indicators.slug = %s and countries.iso2 = 'JP'
              on conflict (source_id, country_id, external_id) do update set display_name = excluded.display_name, unit = excluded.unit
              returning id
            """, (f"{SERIES['database']}:{SERIES['code']}", SERIES["display_name"], SERIES["unit"], SERIES["indicator_slug"]))
            source_series_id = cursor.fetchone()[0]
        connection.commit()
        try:
            inserted = 0
            with connection.cursor() as cursor:
                for period_start, value in observations:
                    raw_observation = {"series_code": SERIES["code"], "period_start": period_start, "value": value, "source_last_update": as_of_date}
                    cursor.execute("""
                      insert into observations (source_series_id, period_start, value, as_of_date, raw_payload)
                      values (%s, %s, %s, %s, %s::jsonb)
                      on conflict (source_series_id, period_start, as_of_date) do nothing
                    """, (source_series_id, period_start, Decimal(str(value)), as_of_date, json.dumps(raw_observation)))
                    inserted += cursor.rowcount
                cursor.execute("update ingestion_runs set status = 'completed', completed_at = now(), records_read = %s, records_written = %s where id = %s", (len(observations), inserted, run_id))
            connection.commit()
            print(f"{SERIES['code']}: {inserted} new observations; official vintage {as_of_date}")
        except Exception as error:
            connection.rollback()
            with connection.cursor() as cursor:
                cursor.execute("update ingestion_runs set status = 'failed', completed_at = now(), error_message = %s where id = %s", (str(error), run_id))
            connection.commit()
            raise


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--start", default="199801", help="Earliest month (YYYYMM)")
    parser.add_argument("--end", default=date.today().strftime("%Y%m"), help="Latest month (YYYYMM)")
    args = parser.parse_args()
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        sys.exit("DATABASE_URL must be set. See ingestion/.env.example.")
    run(database_url, args.start, args.end)


if __name__ == "__main__":
    main()
