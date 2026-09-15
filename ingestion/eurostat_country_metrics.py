"""Ingest official Eurostat macro data for priority European country desks.

The API is free and public. Each immutable observation keeps the exact dataset,
filtered query, release timestamp and any Eurostat observation-status flag.
It covers the same concepts across countries without relabelling an annual
World Bank baseline as a current release.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from calendar import monthrange
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import psycopg

SOURCE_SLUG = "eurostat-data"
API_BASE_URL = "https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data"
COUNTRIES = ("FR", "DE", "IT", "ES", "PL")


@dataclass(frozen=True)
class SeriesDefinition:
    indicator_slug: str
    external_id: str
    display_name: str
    unit: str
    frequency: str
    dataset: str
    parameters: dict[str, str]
    since_time_period: str


SERIES = (
    SeriesDefinition("cpi", "prc_hicp_minr:TOTAL:RCH_A", "HICP Headline Inflation · Annual Rate", "percent", "monthly", "prc_hicp_minr", {"freq": "M", "unit": "RCH_A", "coicop18": "TOTAL"}, "2000-01"),
    SeriesDefinition("core-cpi", "prc_hicp_minr:TOT_X_NRG_FOOD:RCH_A", "HICP Core Inflation · Excluding Energy, Food, Alcohol and Tobacco", "percent", "monthly", "prc_hicp_minr", {"freq": "M", "unit": "RCH_A", "coicop18": "TOT_X_NRG_FOOD"}, "2000-01"),
    SeriesDefinition("unemployment-rate", "une_rt_m:SA:TOTAL:PC_ACT", "Unemployment Rate · Seasonally Adjusted", "percent", "monthly", "une_rt_m", {"freq": "M", "s_adj": "SA", "age": "TOTAL", "unit": "PC_ACT", "sex": "T"}, "2000-01"),
    SeriesDefinition("real-gdp-growth", "namq_10_gdp:CLV_PCH_PRE:SCA:B1GQ", "Real GDP Growth · Quarter on Quarter", "percent", "quarterly", "namq_10_gdp", {"freq": "Q", "unit": "CLV_PCH_PRE", "s_adj": "SCA", "na_item": "B1GQ"}, "2000-Q1"),
    SeriesDefinition("sovereign-10y", "irt_lt_mcby_m:MCBY", "10-Year Government Bond Yield · Maastricht Criterion", "percent", "monthly", "irt_lt_mcby_m", {"freq": "M", "int_rt": "MCBY"}, "2000-01"),
)


def request_url(definition: SeriesDefinition, country_iso2: str) -> str:
    parameters = {**definition.parameters, "geo": country_iso2, "sinceTimePeriod": definition.since_time_period}
    return f"{API_BASE_URL}/{definition.dataset}?{urlencode(parameters)}"


def fetch(definition: SeriesDefinition, country_iso2: str) -> dict:
    url = request_url(definition, country_iso2)
    request = Request(url, headers={"User-Agent": "Muklanovich-Research/0.1 (official Eurostat macro ingestion)"})
    with urlopen(request, timeout=45) as response:
        payload = json.load(response)
    if payload.get("class") != "dataset" or not isinstance(payload.get("value"), dict):
        raise RuntimeError(f"Unexpected Eurostat response for {definition.dataset}/{country_iso2}")
    return payload


def as_of_date(payload: dict) -> str:
    updated = payload.get("updated")
    if not isinstance(updated, str) or len(updated) < 10:
        raise ValueError("Eurostat response has no usable update timestamp")
    return date.fromisoformat(updated[:10]).isoformat()


def period_range(period: str, frequency: str) -> tuple[str, str]:
    if frequency == "monthly":
        year, month = (int(part) for part in period.split("-"))
        return f"{year:04d}-{month:02d}-01", f"{year:04d}-{month:02d}-{monthrange(year, month)[1]:02d}"
    year_text, quarter_text = period.split("-Q")
    year, quarter = int(year_text), int(quarter_text)
    start_month = (quarter - 1) * 3 + 1
    end_month = start_month + 2
    return f"{year:04d}-{start_month:02d}-01", f"{year:04d}-{end_month:02d}-{monthrange(year, end_month)[1]:02d}"


def observations(payload: dict, definition: SeriesDefinition) -> list[tuple[str, str, Decimal, str | None]]:
    time_index = payload.get("dimension", {}).get("time", {}).get("category", {}).get("index", {})
    if not isinstance(time_index, dict):
        raise ValueError("Eurostat response is missing time categories")
    values = payload.get("value", {})
    statuses = payload.get("status", {})
    result: list[tuple[str, str, Decimal, str | None]] = []
    for period, position in sorted(time_index.items(), key=lambda item: item[1]):
        raw_value = values.get(str(position))
        if raw_value is None:
            continue
        period_start, period_end = period_range(period, definition.frequency)
        status = statuses.get(str(position)) if isinstance(statuses, dict) else None
        result.append((period_start, period_end, Decimal(str(raw_value)), status if isinstance(status, str) else None))
    if not result:
        raise RuntimeError(f"Eurostat returned no usable observations for {definition.external_id}")
    return result


def upsert_series(connection: psycopg.Connection, definition: SeriesDefinition, country_iso2: str) -> object:
    with connection.cursor() as cursor:
        cursor.execute(
            """
            insert into source_series (source_id, indicator_id, country_id, external_id, display_name, unit, frequency)
            select sources.id, indicators.id, countries.id, %s, %s, %s, %s
            from sources, indicators, countries
            where sources.slug = %s and indicators.slug = %s and countries.iso2 = %s
            on conflict (source_id, country_id, external_id) do update set
              display_name = excluded.display_name,
              unit = excluded.unit,
              frequency = excluded.frequency
            returning id
            """,
            (definition.external_id, definition.display_name, definition.unit, definition.frequency, SOURCE_SLUG, definition.indicator_slug, country_iso2),
        )
        row = cursor.fetchone()
        if row is None:
            raise RuntimeError(f"Database bootstrap is incomplete for {definition.indicator_slug}/{country_iso2}")
        return row[0]


def write_observations(
    connection: psycopg.Connection,
    source_series_id: object,
    definition: SeriesDefinition,
    country_iso2: str,
    payload: dict,
) -> tuple[int, int]:
    vintage = as_of_date(payload)
    source_url = request_url(definition, country_iso2)
    points = observations(payload, definition)
    inserted = 0
    with connection.cursor() as cursor:
        for period_start, period_end, value, status in points:
            raw_payload = {
                "dataset": definition.dataset,
                "query_url": source_url,
                "country": country_iso2,
                "official_updated": payload["updated"],
                "observation_status": status,
                "source": payload.get("source"),
            }
            cursor.execute(
                """
                insert into observations (source_series_id, period_start, period_end, value, as_of_date, raw_payload)
                values (%s, %s, %s, %s, %s, %s::jsonb)
                on conflict (source_series_id, period_start, as_of_date) do nothing
                """,
                (source_series_id, period_start, period_end, value, vintage, json.dumps(raw_payload)),
            )
            inserted += cursor.rowcount
    return len(points), inserted


def run(database_url: str) -> None:
    with psycopg.connect(database_url) as connection:
        with connection.cursor() as cursor:
            cursor.execute("insert into ingestion_runs (source_id, status) select id, 'started' from sources where slug = %s returning id", (SOURCE_SLUG,))
            row = cursor.fetchone()
            if row is None:
                raise RuntimeError("Apply database/migrations/024_eurostat_country_metrics.sql first.")
            run_id = row[0]
        connection.commit()
        try:
            records_read = 0
            records_written = 0
            for country_iso2 in COUNTRIES:
                for definition in SERIES:
                    payload = fetch(definition, country_iso2)
                    source_series_id = upsert_series(connection, definition, country_iso2)
                    read, written = write_observations(connection, source_series_id, definition, country_iso2, payload)
                    records_read += read
                    records_written += written
                    print(f"{country_iso2} {definition.indicator_slug}: {read} observed, {written} new")
            with connection.cursor() as cursor:
                cursor.execute(
                    "update ingestion_runs set status = 'completed', completed_at = now(), records_read = %s, records_written = %s where id = %s",
                    (records_read, records_written, run_id),
                )
            connection.commit()
        except Exception as error:
            connection.rollback()
            with connection.cursor() as cursor:
                cursor.execute("update ingestion_runs set status = 'failed', completed_at = now(), error_message = %s where id = %s", (str(error), run_id))
            connection.commit()
            raise


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args()
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        sys.exit("DATABASE_URL must be set. See ingestion/.env.example.")
    run(database_url)


if __name__ == "__main__":
    main()
