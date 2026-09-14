"""Ingest a reproducible US macro baseline from FRED/ALFRED into PostgreSQL.

The worker intentionally stores every raw response and does not overwrite an
existing (series, period, vintage) observation. This preserves data revisions
for later research and scenario evaluation.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation
from urllib.parse import urlencode
from urllib.error import HTTPError
from urllib.request import urlopen

import psycopg

FRED_OBSERVATIONS_URL = "https://api.stlouisfed.org/fred/series/observations"


@dataclass(frozen=True)
class SeriesDefinition:
    indicator_slug: str
    fred_series_id: str
    display_name: str
    unit: str


US_SERIES = (
    SeriesDefinition("policy-rate", "DFF", "Effective Federal Funds Rate", "percent"),
    SeriesDefinition("cpi", "CPIAUCSL", "Consumer Price Index", "index"),
    SeriesDefinition("unemployment-rate", "UNRATE", "Unemployment Rate", "percent"),
    SeriesDefinition("nonfarm-payrolls", "PAYEMS", "All Employees: Total Nonfarm", "thousands of persons"),
    SeriesDefinition("real-gdp", "GDPC1", "Real Gross Domestic Product", "billions of chained dollars"),
    SeriesDefinition("treasury-2y", "DGS2", "2-Year US Treasury Yield", "percent"),
    SeriesDefinition("treasury-10y", "DGS10", "10-Year US Treasury Yield", "percent"),
)

JAPAN_SERIES = (
    SeriesDefinition("policy-rate", "IRSTCB01JPM156N", "Bank of Japan Central Bank Rate", "percent"),
    SeriesDefinition("cpi", "JPNCPIALLMINMEI", "Japan Consumer Price Index", "index"),
    SeriesDefinition("unemployment-rate", "LRUNTTTTJPM156S", "Japan Unemployment Rate", "percent"),
    SeriesDefinition("real-gdp", "JPNRGDPEXP", "Japan Real Gross Domestic Product", "billions of yen"),
    SeriesDefinition("treasury-10y", "IRLTLT01JPM156N", "Japan 10-Year Government Bond Yield", "percent"),
)

COUNTRY_SERIES = {"US": US_SERIES, "JP": JAPAN_SERIES}


def fetch_observations(api_key: str, series_id: str, observation_start: str) -> dict:
    query = urlencode({
        "api_key": api_key,
        "file_type": "json",
        "series_id": series_id,
        "observation_start": observation_start,
    })
    try:
        with urlopen(f"{FRED_OBSERVATIONS_URL}?{query}", timeout=30) as response:
            return json.load(response)
    except HTTPError as error:
        detail = error.read().decode("utf-8", errors="replace").strip()
        raise RuntimeError(f"FRED request failed for {series_id} ({error.code}): {detail}") from error


def as_decimal(value: str) -> Decimal | None:
    if value in {".", "", None}:
        return None
    try:
        return Decimal(value)
    except InvalidOperation as error:
        raise ValueError(f"FRED returned a non-numeric value: {value!r}") from error


def upsert_series(connection: psycopg.Connection, definition: SeriesDefinition, country_iso2: str) -> int:
    with connection.cursor() as cursor:
        cursor.execute("""
            insert into source_series (source_id, indicator_id, country_id, external_id, display_name, unit)
            select sources.id, indicators.id, countries.id, %s, %s, %s
            from sources, indicators, countries
            where sources.slug = 'fred' and indicators.slug = %s and countries.iso2 = %s
            on conflict (source_id, country_id, external_id) do update set display_name = excluded.display_name, unit = excluded.unit
            returning id
        """, (definition.fred_series_id, definition.display_name, definition.unit, definition.indicator_slug, country_iso2))
        row = cursor.fetchone()
        if row is None:
            raise RuntimeError(f"Database bootstrap is incomplete for {definition.indicator_slug}")
        return row[0]


def write_observations(connection: psycopg.Connection, source_series_id: int, payload: dict) -> int:
    inserted = 0
    with connection.cursor() as cursor:
        for observation in payload.get("observations", []):
            vintage = observation.get("realtime_start") or date.today().isoformat()
            cursor.execute("""
                insert into observations (
                    source_series_id, period_start, value, as_of_date, raw_payload
                ) values (%s, %s, %s, %s, %s::jsonb)
                on conflict (source_series_id, period_start, as_of_date) do nothing
            """, (
                source_series_id,
                observation["date"],
                as_decimal(observation.get("value")),
                vintage,
                json.dumps(observation),
            ))
            inserted += cursor.rowcount
    return inserted


def run(database_url: str, api_key: str, observation_start: str, country_iso2: str) -> None:
    definitions = COUNTRY_SERIES[country_iso2]
    with psycopg.connect(database_url) as connection:
        for definition in definitions:
            with connection.cursor() as cursor:
                cursor.execute("insert into ingestion_runs (source_id, status) select id, 'started' from sources where slug = 'fred' returning id")
                run_id = cursor.fetchone()[0]
            connection.commit()
            try:
                payload = fetch_observations(api_key, definition.fred_series_id, observation_start)
                source_series_id = upsert_series(connection, definition, country_iso2)
                records_written = write_observations(connection, source_series_id, payload)
                with connection.cursor() as cursor:
                    cursor.execute("update ingestion_runs set status = 'completed', completed_at = now(), records_read = %s, records_written = %s where id = %s", (len(payload.get("observations", [])), records_written, run_id))
                connection.commit()
                print(f"{definition.fred_series_id}: {records_written} new observations")
            except Exception as error:
                connection.rollback()
                with connection.cursor() as cursor:
                    cursor.execute("update ingestion_runs set status = 'failed', completed_at = now(), error_message = %s where id = %s", (str(error), run_id))
                connection.commit()
                raise


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--start", default="1990-01-01", help="Earliest observation date (YYYY-MM-DD)")
    parser.add_argument("--country", choices=COUNTRY_SERIES.keys(), default="US", help="Country ISO-2 code")
    args = parser.parse_args()
    database_url = os.environ.get("DATABASE_URL")
    api_key = os.environ.get("FRED_API_KEY")
    if not database_url or not api_key:
        sys.exit("DATABASE_URL and FRED_API_KEY must be set. See ingestion/.env.example.")
    run(database_url, api_key, args.start, args.country)


if __name__ == "__main__":
    main()
