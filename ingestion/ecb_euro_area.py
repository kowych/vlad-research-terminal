"""Ingest the ECB main refinancing operations rate for priority euro-area desks."""

from __future__ import annotations

import argparse
import csv
import io
import json
import os
import sys
from datetime import date
from decimal import Decimal
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import psycopg

ECB_DATA_URL = "https://data-api.ecb.europa.eu/service/data/FM/B.U2.EUR.4F.KR.MRR_FR.LEV"
COUNTRIES = ("FR", "DE", "IT", "ES")
SERIES = {
    "indicator_slug": "policy-rate",
    "external_id": "FM.B.U2.EUR.4F.KR.MRR_FR.LEV",
    "display_name": "ECB Main Refinancing Operations Rate",
    "unit": "percent per annum",
}


def fetch(start_period: str) -> list[dict[str, str]]:
    query = urlencode({"format": "csvdata", "startPeriod": start_period})
    request = Request(f"{ECB_DATA_URL}?{query}", headers={"User-Agent": "Muklanovich-Research/0.1 (local macro research)"})
    with urlopen(request, timeout=30) as response:
        rows = list(csv.DictReader(io.TextIOWrapper(response, encoding="utf-8-sig")))
    if not rows or "TIME_PERIOD" not in rows[0] or "OBS_VALUE" not in rows[0]:
        raise RuntimeError("Unexpected ECB CSV response")
    return rows


def run(database_url: str, start_period: str) -> None:
    rows = fetch(start_period)
    retrieved_on = date.today().isoformat()
    observations = [
        (row["TIME_PERIOD"], row["OBS_VALUE"])
        for row in rows
        if row["OBS_VALUE"].strip() and date.fromisoformat(row["TIME_PERIOD"]) <= date.today()
    ]
    with psycopg.connect(database_url) as connection:
        for country_iso2 in COUNTRIES:
            with connection.cursor() as cursor:
                cursor.execute("insert into ingestion_runs (source_id, status) select id, 'started' from sources where slug = 'ecb-data-portal' returning id")
                run_id = cursor.fetchone()[0]
                cursor.execute("""
                  insert into source_series (source_id, indicator_id, country_id, external_id, display_name, unit, frequency)
                  select sources.id, indicators.id, countries.id, %s, %s, %s, 'daily' from sources, indicators, countries
                  where sources.slug = 'ecb-data-portal' and indicators.slug = %s and countries.iso2 = %s
                  on conflict (source_id, country_id, external_id) do update set display_name = excluded.display_name, unit = excluded.unit, frequency = excluded.frequency
                  returning id
                """, (SERIES["external_id"], SERIES["display_name"], SERIES["unit"], SERIES["indicator_slug"], country_iso2))
                source_series_id = cursor.fetchone()[0]
            connection.commit()
            try:
                inserted = 0
                with connection.cursor() as cursor:
                    for period_start, value in observations:
                        raw_observation = {"series_key": SERIES["external_id"], "period_start": period_start, "value": value, "retrieved_on": retrieved_on}
                        cursor.execute("""
                          insert into observations (source_series_id, period_start, value, as_of_date, raw_payload)
                          values (%s, %s, %s, %s, %s::jsonb)
                          on conflict (source_series_id, period_start, as_of_date) do nothing
                        """, (source_series_id, period_start, Decimal(value), retrieved_on, json.dumps(raw_observation)))
                        inserted += cursor.rowcount
                    cursor.execute("update ingestion_runs set status = 'completed', completed_at = now(), records_read = %s, records_written = %s where id = %s", (len(observations), inserted, run_id))
                connection.commit()
                print(f"{country_iso2}: {inserted} new ECB MRO observations; official database retrieved {retrieved_on}")
            except Exception as error:
                connection.rollback()
                with connection.cursor() as cursor:
                    cursor.execute("update ingestion_runs set status = 'failed', completed_at = now(), error_message = %s where id = %s", (str(error), run_id))
                connection.commit()
                raise


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--start", default="1999-01-01", help="Earliest observation date (YYYY-MM-DD)")
    args = parser.parse_args()
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        sys.exit("DATABASE_URL must be set. See ingestion/.env.example.")
    run(database_url, args.start)


if __name__ == "__main__":
    main()
