"""Ingest Australia's six desk metrics from official RBA statistical tables.

RBA publishes the tables as public CSV files. The worker records the RBA
series identifier, table URL and publication date with each immutable
observation, so a later model can inspect the exact provenance without
depending on a presentation-layer chart or a third-party aggregator.
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import os
import subprocess
import sys
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

import psycopg

SOURCE_SLUG = "reserve-bank-australia-data"


@dataclass(frozen=True)
class SeriesDefinition:
    indicator_slug: str
    series_id: str
    display_name: str
    unit: str
    frequency: str
    table_name: str
    table_url: str


SERIES = (
    SeriesDefinition("policy-rate", "FIRMMCRT", "Cash Rate Target", "percent", "monthly", "RBA Table F1.1 · Money Market Rates and Yields", "https://www.rba.gov.au/statistics/tables/csv/f1.1-data.csv"),
    SeriesDefinition("cpi", "GCPIAG", "Consumer Price Index · All Groups", "index", "quarterly", "RBA Table G1 · Consumer Price Inflation", "https://www.rba.gov.au/statistics/tables/csv/g1-data.csv"),
    SeriesDefinition("core-cpi", "GCPIOCPMTMYP", "Trimmed Mean Inflation · Year-ended", "percent", "quarterly", "RBA Table G1 · Consumer Price Inflation", "https://www.rba.gov.au/statistics/tables/csv/g1-data.csv"),
    SeriesDefinition("unemployment-rate", "GLFSURSA", "Unemployment Rate", "percent", "monthly", "RBA Table H5 · Labour Market", "https://www.rba.gov.au/statistics/tables/csv/h5-data.csv"),
    SeriesDefinition("real-gdp-growth", "GGDPCVGDPY", "Real GDP Growth · Year-ended", "percent", "quarterly", "RBA Table H1 · GDP and Income", "https://www.rba.gov.au/statistics/tables/csv/h1-data.csv"),
    SeriesDefinition("sovereign-10y", "FCMYGBAG10", "Australian Government 10-Year Bond Yield", "percent", "monthly", "RBA Table F2.1 · Capital Market Yields", "https://www.rba.gov.au/statistics/tables/csv/f2.1-data.csv"),
)


def fetch_csv(url: str) -> str:
    """Use curl for the public RBA file endpoint, which rejects urllib traffic.

    No browser identity or access-control workaround is used; this is a normal
    public-file request and a failed download is reported in ingestion health.
    """
    result = subprocess.run(
        ["curl", "--fail", "--silent", "--show-error", "--location", "--connect-timeout", "15", "--max-time", "45", url],
        capture_output=True,
        check=False,
        text=True,
    )
    if result.returncode:
        raise RuntimeError(f"RBA table download failed: {result.stderr.strip() or result.returncode}")
    return result.stdout


def label(value: str) -> str:
    return value.removeprefix("\ufeff").strip()


def parse_publication_date(value: str) -> str:
    try:
        return datetime.strptime(value.strip(), "%d-%b-%Y").date().isoformat()
    except ValueError as error:
        raise ValueError(f"Unexpected RBA publication date: {value!r}") from error


def parse_period_start(value: str) -> str:
    for pattern in ("%d-%b-%Y", "%d/%m/%Y"):
        try:
            return datetime.strptime(value.strip(), pattern).date().isoformat()
        except ValueError:
            continue
    raise ValueError(f"Unexpected RBA observation date: {value!r}")


def as_decimal(value: str) -> Decimal | None:
    cleaned = value.strip().replace(",", "")
    if cleaned.lower() in {"", "n.a.", "na", "-"}:
        return None
    try:
        return Decimal(cleaned)
    except InvalidOperation as error:
        raise ValueError(f"RBA returned a non-numeric value: {value!r}") from error


def canonical_period(observed_on: str, frequency: str) -> tuple[str, str]:
    """Map RBA end-of-period dates to the schema's start/end interval pair."""
    value = date.fromisoformat(observed_on)
    if frequency == "monthly":
        return value.replace(day=1).isoformat(), observed_on
    if frequency == "quarterly":
        quarter_start_month = ((value.month - 1) // 3) * 3 + 1
        return value.replace(month=quarter_start_month, day=1).isoformat(), observed_on
    return observed_on, observed_on


def parse_table(text: str, definitions: tuple[SeriesDefinition, ...]) -> dict[str, tuple[str, list[tuple[str, str, Decimal]], str]]:
    """Return publication date and observations for each requested table series."""
    rows = list(csv.reader(io.StringIO(text)))
    metadata: dict[str, list[str]] = {}
    series_header_index = -1
    for index, row in enumerate(rows):
        if not row:
            continue
        key = label(row[0])
        metadata[key] = row[1:]
        if key == "Series ID":
            series_header_index = index
            break
    if series_header_index < 0:
        raise ValueError("RBA CSV does not include a Series ID row")

    series_ids = metadata.get("Series ID", [])
    publication_dates = metadata.get("Publication date", [])
    parsed: dict[str, tuple[str, list[tuple[str, str, Decimal]], str]] = {}
    for definition in definitions:
        try:
            column = series_ids.index(definition.series_id)
            published_on = parse_publication_date(publication_dates[column])
        except (ValueError, IndexError) as error:
            raise ValueError(f"RBA table is missing {definition.series_id} or its publication date") from error

        observations: list[tuple[str, str, Decimal]] = []
        for row in rows[series_header_index + 1:]:
            if len(row) <= column + 1:
                continue
            try:
                period_start, period_end = canonical_period(parse_period_start(label(row[0])), definition.frequency)
            except ValueError:
                continue
            value = as_decimal(row[column + 1])
            if value is not None:
                observations.append((period_start, period_end, value))
        if not observations:
            raise ValueError(f"RBA table has no observations for {definition.series_id}")
        parsed[definition.series_id] = (published_on, observations, definition.table_name)
    return parsed


def upsert_series(connection: psycopg.Connection, definition: SeriesDefinition) -> object:
    with connection.cursor() as cursor:
        cursor.execute(
            """
            insert into source_series (source_id, indicator_id, country_id, external_id, display_name, unit, frequency)
            select sources.id, indicators.id, countries.id, %s, %s, %s, %s
            from sources, indicators, countries
            where sources.slug = %s and indicators.slug = %s and countries.iso2 = 'AU'
            on conflict (source_id, country_id, external_id) do update set
              display_name = excluded.display_name,
              unit = excluded.unit,
              frequency = excluded.frequency
            returning id
            """,
            (definition.series_id, definition.display_name, definition.unit, definition.frequency, SOURCE_SLUG, definition.indicator_slug),
        )
        row = cursor.fetchone()
        if row is None:
            raise RuntimeError(f"Database bootstrap is incomplete for {definition.indicator_slug}")
        return row[0]


def write_observations(
    connection: psycopg.Connection,
    source_series_id: object,
    definition: SeriesDefinition,
    published_on: str,
    observations: list[tuple[str, str, Decimal]],
) -> int:
    written = 0
    with connection.cursor() as cursor:
        for period_start, period_end, value in observations:
            payload = {
                "series_id": definition.series_id,
                "table_name": definition.table_name,
                "table_url": definition.table_url,
                "publication_date": published_on,
                "observed_on": period_end,
                "frequency": definition.frequency,
                "unit": definition.unit,
            }
            cursor.execute(
                """
                insert into observations (source_series_id, period_start, period_end, value, as_of_date, raw_payload)
                values (%s, %s, %s, %s, %s, %s::jsonb)
                on conflict (source_series_id, period_start, as_of_date) do nothing
                """,
                (source_series_id, period_start, period_end, value, published_on, json.dumps(payload)),
            )
            written += cursor.rowcount
    return written


def run(database_url: str) -> None:
    tables = {definition.table_url: tuple(item for item in SERIES if item.table_url == definition.table_url) for definition in SERIES}
    with psycopg.connect(database_url) as connection:
        with connection.cursor() as cursor:
            cursor.execute("insert into ingestion_runs (source_id, status) select id, 'started' from sources where slug = %s returning id", (SOURCE_SLUG,))
            run_id = cursor.fetchone()[0]
        connection.commit()
        try:
            parsed_tables = {url: parse_table(fetch_csv(url), definitions) for url, definitions in tables.items()}
            records_read = 0
            records_written = 0
            for definition in SERIES:
                published_on, observations, _table_name = parsed_tables[definition.table_url][definition.series_id]
                source_series_id = upsert_series(connection, definition)
                records_read += len(observations)
                records_written += write_observations(connection, source_series_id, definition, published_on, observations)
                print(f"{definition.series_id}: {len(observations)} observed, {records_written} total new")
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
