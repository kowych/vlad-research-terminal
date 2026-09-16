"""Ingest a reproducible, free daily FX history for the macro country desks.

The canonical value is always USD per one unit of local currency. Providers
often publish the opposite convention (for example CAD per foreign currency),
so every source value, its original quote convention and the transformation are
preserved in ``observations.raw_payload``. These are daily reference rates, not
intraday executable prices.

Bank of Canada Valet covers the liquid currencies in the country universe. The
National Bank of Ukraine and Bank of Russia provide first-party USD reference
rates for UAH and RUB. Iran is deliberately excluded: multiple regulated and
market IRR rates make a single "FX vs USD" series misleading without an
explicit rate-regime policy and a suitable authorised source.
"""
from __future__ import annotations

import argparse
import csv
import io
import json
import os
import sys
import xml.etree.ElementTree as ElementTree
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal, InvalidOperation
from typing import Any, Iterable
from urllib.parse import urlencode
from urllib.request import urlopen

import psycopg


BOC_SOURCE = "bank-of-canada-valet-fx"
NBU_SOURCE = "national-bank-ukraine-fx"
CBR_SOURCE = "bank-of-russia-fx"
CANONICAL_UNIT = "USD per local currency"
BOC_OBSERVATIONS_URL = "https://www.bankofcanada.ca/valet/observations"
ECB_EXR_URL = "https://data-api.ecb.europa.eu/service/data/EXR"
NBU_HISTORY_URL = "https://bank.gov.ua/NBU_Exchange/exchange_site"
CBR_HISTORY_URL = "https://www.cbr.ru/scripts/XML_dynamic.asp"


@dataclass(frozen=True)
class BocCurrency:
    country_iso2: str
    currency: str
    series_id: str | None


# Bank of Canada values are CAD per one unit of the foreign currency. CAD is
# derived as the reciprocal of USD/CAD, which gives every country a consistent
# USD-per-local-currency series after a transparent cross calculation.
BOC_CURRENCIES = (
    BocCurrency("AU", "AUD", "FXAUDCAD"),
    BocCurrency("CA", "CAD", None),
    BocCurrency("CN", "CNY", "FXCNYCAD"),
    BocCurrency("CH", "CHF", "FXCHFCAD"),
    BocCurrency("DE", "EUR", "FXEURCAD"),
    BocCurrency("ES", "EUR", "FXEURCAD"),
    BocCurrency("FR", "EUR", "FXEURCAD"),
    BocCurrency("GB", "GBP", "FXGBPCAD"),
    BocCurrency("IN", "INR", "FXINRCAD"),
    BocCurrency("IT", "EUR", "FXEURCAD"),
    BocCurrency("JP", "JPY", "FXJPYCAD"),
    BocCurrency("KR", "KRW", "FXKRWCAD"),
    BocCurrency("NO", "NOK", "FXNOKCAD"),
    BocCurrency("NZ", "NZD", "FXNZDCAD"),
    BocCurrency("PL", "PLN", "FXPLNCAD"),
    BocCurrency("SE", "SEK", "FXSEKCAD"),
    BocCurrency("TR", "TRY", "FXTRYCAD"),
)


def fetch_json(url: str, query: dict[str, str]) -> dict[str, Any] | list[dict[str, Any]]:
    request_url = f"{url}?{urlencode(query)}"
    with urlopen(request_url, timeout=60) as response:
        return json.load(response)


def fetch_text(url: str, query: dict[str, str]) -> str:
    request_url = f"{url}?{urlencode(query)}"
    with urlopen(request_url, timeout=60) as response:
        return response.read().decode("windows-1251")


def fetch_utf8_text(url: str, query: dict[str, str]) -> str:
    request_url = f"{url}?{urlencode(query)}"
    with urlopen(request_url, timeout=60) as response:
        return response.read().decode("utf-8")


def decimal(value: object) -> Decimal | None:
    if value in {None, "", "."}:
        return None
    try:
        return Decimal(str(value).replace(",", "."))
    except InvalidOperation as error:
        raise ValueError(f"Source returned a non-numeric FX value: {value!r}") from error


def parse_date(value: str) -> str:
    if len(value) == 10 and value[4] == "-":
        return value
    day, month, year = value.split(".")
    return f"{year}-{month}-{day}"


def yearly_windows(start: date, end: date) -> Iterable[tuple[date, date]]:
    current = start
    while current <= end:
        next_year = date(current.year + 1, current.month, current.day)
        window_end = min(end, next_year.fromordinal(next_year.toordinal() - 1))
        yield current, window_end
        current = next_year


def source_id(connection: psycopg.Connection, slug: str) -> object:
    with connection.cursor() as cursor:
        cursor.execute("select id from sources where slug = %s", (slug,))
        row = cursor.fetchone()
    if row is None:
        raise RuntimeError(f"Database migration is missing source {slug!r}")
    return row[0]


def begin_run(connection: psycopg.Connection, slug: str) -> object:
    with connection.cursor() as cursor:
        cursor.execute("insert into ingestion_runs (source_id, status) values (%s, 'started') returning id", (source_id(connection, slug),))
        run_id = cursor.fetchone()[0]
    connection.commit()
    return run_id


def complete_run(connection: psycopg.Connection, run_id: object, records_read: int, records_written: int) -> None:
    with connection.cursor() as cursor:
        cursor.execute(
            "update ingestion_runs set status = 'completed', completed_at = now(), records_read = %s, records_written = %s where id = %s",
            (records_read, records_written, run_id),
        )
    connection.commit()


def fail_run(connection: psycopg.Connection, run_id: object, error: Exception) -> None:
    connection.rollback()
    with connection.cursor() as cursor:
        cursor.execute(
            "update ingestion_runs set status = 'failed', completed_at = now(), error_message = %s where id = %s",
            (str(error), run_id),
        )
    connection.commit()


def upsert_series(connection: psycopg.Connection, source_slug: str, country_iso2: str, external_id: str, display_name: str) -> object:
    with connection.cursor() as cursor:
        cursor.execute(
            """
            insert into source_series (source_id, indicator_id, country_id, external_id, display_name, unit, frequency)
            select sources.id, indicators.id, countries.id, %s, %s, %s, 'daily'
            from sources, indicators, countries
            where sources.slug = %s and indicators.slug = 'fx-usd' and countries.iso2 = %s
            on conflict (source_id, country_id, external_id) do update set
              display_name = excluded.display_name, unit = excluded.unit, frequency = excluded.frequency
            returning id
            """,
            (external_id, display_name, CANONICAL_UNIT, source_slug, country_iso2),
        )
        row = cursor.fetchone()
    if row is None:
        raise RuntimeError(f"Database bootstrap is incomplete for {country_iso2} FX")
    return row[0]


def write_observation(
    connection: psycopg.Connection,
    series_id: object,
    period_start: str,
    value: Decimal,
    as_of_date: str,
    raw_payload: dict[str, object],
) -> int:
    with connection.cursor() as cursor:
        cursor.execute(
            """
            insert into observations (source_series_id, period_start, value, as_of_date, raw_payload)
            values (%s, %s, %s, %s, %s::jsonb)
            on conflict (source_series_id, period_start, as_of_date) do nothing
            """,
            (series_id, period_start, value, as_of_date, json.dumps(raw_payload)),
        )
        return cursor.rowcount


def run_boc(connection: psycopg.Connection, start: date, end: date) -> tuple[int, int]:
    run_id = begin_run(connection, BOC_SOURCE)
    try:
        currencies_by_series = {item.series_id: item for item in BOC_CURRENCIES if item.series_id}
        series_names = ["FXUSDCAD", *currencies_by_series]
        series_by_country = {
            item.country_iso2: upsert_series(
                connection,
                BOC_SOURCE,
                item.country_iso2,
                item.series_id or "FXUSDCAD:CAD-RECIPROCAL",
                f"{item.currency} / USD · daily reference rate",
            )
            for item in BOC_CURRENCIES
        }
        records_read = 0
        records_written = 0
        for window_start, window_end in yearly_windows(start, end):
            payload = fetch_json(
                f"{BOC_OBSERVATIONS_URL}/{','.join(series_names)}/json",
                {"start_date": window_start.isoformat(), "end_date": window_end.isoformat()},
            )
            if not isinstance(payload, dict):
                raise ValueError("Unexpected Bank of Canada response")
            for observed in payload.get("observations", []):
                observed_on = observed.get("d")
                usd_per_cad = decimal((observed.get("FXUSDCAD") or {}).get("v"))
                if not isinstance(observed_on, str) or usd_per_cad is None or usd_per_cad <= 0:
                    continue
                for currency in BOC_CURRENCIES:
                    source_value = Decimal(1) if currency.series_id is None else decimal((observed.get(currency.series_id) or {}).get("v"))
                    if source_value is None or source_value <= 0:
                        continue
                    canonical_value = (Decimal(1) / usd_per_cad) if currency.series_id is None else source_value / usd_per_cad
                    raw_payload = {
                        "provider": "Bank of Canada Valet",
                        "provider_url": "https://www.bankofcanada.ca/valet/docs/",
                        "observation_date": observed_on,
                        "source_series": currency.series_id or "FXUSDCAD",
                        "source_value": str(source_value),
                        "source_quote": "CAD per 1 unit of local currency" if currency.series_id else "CAD per 1 USD",
                        "usd_cad_source_value": str(usd_per_cad),
                        "canonical_quote": "USD per 1 unit of local currency",
                        "canonical_value": str(canonical_value),
                        "transformation": "1 / USD/CAD" if currency.series_id is None else "(CAD per local currency) / (CAD per USD)",
                        "rate_type": "daily_indicative_reference",
                    }
                    records_written += write_observation(connection, series_by_country[currency.country_iso2], observed_on, canonical_value, observed_on, raw_payload)
                    records_read += 1
        complete_run(connection, run_id, records_read, records_written)
        return records_read, records_written
    except Exception as error:
        fail_run(connection, run_id, error)
        raise


def fetch_ecb_series(currencies: Iterable[str], start: date, end: date) -> dict[str, dict[str, Decimal]]:
    """Return ECB daily reference rates quoted as ``currency per EUR``.

    ECB supports multiple currency codes in one SDMX series key. One batched
    download is materially faster and gentler on the public API than issuing a
    separate 20-year request per currency.
    """
    requested = tuple(sorted(set(currencies)))
    payload = fetch_utf8_text(
        f"{ECB_EXR_URL}/D.{'+'.join(requested)}.EUR.SP00.A",
        {"startPeriod": start.isoformat(), "endPeriod": end.isoformat(), "format": "csvdata"},
    )
    rates = {currency: {} for currency in requested}
    for row in csv.DictReader(io.StringIO(payload)):
        currency = row.get("CURRENCY")
        observed_on = row.get("TIME_PERIOD")
        value = decimal(row.get("OBS_VALUE"))
        if currency in rates and observed_on and value is not None and value > 0:
            rates[currency][observed_on] = value
    missing = [currency for currency, observations in rates.items() if not observations]
    if missing:
        raise ValueError(f"ECB did not return usable reference-rate observations for: {', '.join(missing)}")
    return rates


def run_ecb(connection: psycopg.Connection, start: date, end: date) -> tuple[int, int]:
    """Backfill a 20-year FX history from official ECB reference rates.

    The ECB publishes each local currency against EUR. Combining each series
    with USD/EUR on the same reference date yields ``USD per local currency``
    without using a vendor cross or silently mixing quote conventions.
    """
    run_id = begin_run(connection, "ecb-data-portal")
    try:
        print("ECB: fetching batched daily reference-rate history…", flush=True)
        rates = fetch_ecb_series(("USD", *(item.currency for item in BOC_CURRENCIES if item.currency != "EUR")), start, end)
        usd_per_eur = rates["USD"]
        local_rates = rates
        series_by_country = {
            item.country_iso2: upsert_series(
                connection,
                "ecb-data-portal",
                item.country_iso2,
                "EXR.D.USD.EUR.SP00.A" if item.currency == "EUR" else f"EXR.D.{item.currency}.EUR.SP00.A",
                f"{item.currency} / USD · ECB reference rate",
            )
            for item in BOC_CURRENCIES
        }
        records_read = 0
        records_written = 0
        print("ECB: writing canonical USD cross-rates…", flush=True)
        for currency in BOC_CURRENCIES:
            if currency.currency == "EUR":
                pairs = ((observed_on, value, None) for observed_on, value in usd_per_eur.items())
            else:
                pairs = (
                    (observed_on, usd_value, local_rates[currency.currency].get(observed_on))
                    for observed_on, usd_value in usd_per_eur.items()
                )
            for observed_on, usd_value, local_per_eur in pairs:
                if currency.currency != "EUR" and local_per_eur is None:
                    continue
                if local_per_eur is not None and local_per_eur <= 0:
                    continue
                canonical_value = usd_value if local_per_eur is None else usd_value / local_per_eur
                raw_payload = {
                    "provider": "European Central Bank Data Portal",
                    "provider_url": "https://data.ecb.europa.eu/",
                    "observation_date": observed_on,
                    "usd_eur_series": "EXR.D.USD.EUR.SP00.A",
                    "usd_per_eur": str(usd_value),
                    "local_eur_series": None if local_per_eur is None else f"EXR.D.{currency.currency}.EUR.SP00.A",
                    "local_per_eur": None if local_per_eur is None else str(local_per_eur),
                    "canonical_quote": "USD per 1 unit of local currency",
                    "canonical_value": str(canonical_value),
                    "transformation": "USD per EUR" if local_per_eur is None else "(USD per EUR) / (local currency per EUR)",
                    "rate_type": "daily_reference",
                }
                records_written += write_observation(
                    connection,
                    series_by_country[currency.country_iso2],
                    observed_on,
                    canonical_value,
                    observed_on,
                    raw_payload,
                )
                records_read += 1
        complete_run(connection, run_id, records_read, records_written)
        return records_read, records_written
    except Exception as error:
        fail_run(connection, run_id, error)
        raise


def run_nbu(connection: psycopg.Connection, start: date, end: date) -> tuple[int, int]:
    run_id = begin_run(connection, NBU_SOURCE)
    try:
        payload = fetch_json(
            NBU_HISTORY_URL,
            {
                "start": start.strftime("%Y%m%d"),
                "end": end.strftime("%Y%m%d"),
                "valcode": "usd",
                "sort": "exchangedate",
                "order": "asc",
                "json": "",
            },
        )
        if not isinstance(payload, list):
            raise ValueError("Unexpected National Bank of Ukraine response")
        series_id = upsert_series(connection, NBU_SOURCE, "UA", "USD-UAH-OFFICIAL", "UAH / USD · official reference rate")
        written = 0
        read = 0
        for observed in payload:
            period_start = parse_date(str(observed["exchangedate"]))
            uah_per_usd = decimal(observed.get("rate_per_unit") or observed.get("rate"))
            if uah_per_usd is None or uah_per_usd <= 0:
                continue
            canonical_value = Decimal(1) / uah_per_usd
            publication_date = str(observed.get("calcdate") or "").strip() or str(observed["exchangedate"])
            as_of_date = parse_date(publication_date)
            raw_payload = {
                "provider": "National Bank of Ukraine",
                "provider_url": "https://bank.gov.ua/en/markets/exchangerates",
                "source_quote": "UAH per 1 USD",
                "source_value": str(uah_per_usd),
                "canonical_quote": "USD per 1 UAH",
                "canonical_value": str(canonical_value),
                "transformation": "1 / (UAH per USD)",
                "rate_type": "official_reference",
                "provider_payload": observed,
            }
            written += write_observation(connection, series_id, period_start, canonical_value, as_of_date, raw_payload)
            read += 1
        complete_run(connection, run_id, read, written)
        return read, written
    except Exception as error:
        fail_run(connection, run_id, error)
        raise


def run_cbr(connection: psycopg.Connection, start: date, end: date) -> tuple[int, int]:
    run_id = begin_run(connection, CBR_SOURCE)
    try:
        payload = fetch_text(
            CBR_HISTORY_URL,
            {"date_req1": start.strftime("%d/%m/%Y"), "date_req2": end.strftime("%d/%m/%Y"), "VAL_NM_RQ": "R01235"},
        )
        root = ElementTree.fromstring(payload)
        series_id = upsert_series(connection, CBR_SOURCE, "RU", "R01235", "RUB / USD · official reference rate")
        written = 0
        read = 0
        for record in root.findall("Record"):
            period_start = parse_date(record.attrib["Date"])
            nominal = decimal(record.findtext("Nominal"))
            rub_per_nominal = decimal(record.findtext("Value"))
            if nominal is None or rub_per_nominal is None or nominal <= 0 or rub_per_nominal <= 0:
                continue
            rub_per_usd = rub_per_nominal / nominal
            canonical_value = Decimal(1) / rub_per_usd
            raw_payload = {
                "provider": "Bank of Russia",
                "provider_url": "https://www.cbr.ru/eng/currency_base/daily/",
                "source_series": "R01235",
                "source_quote": "RUB per 1 USD",
                "source_value": str(rub_per_usd),
                "canonical_quote": "USD per 1 RUB",
                "canonical_value": str(canonical_value),
                "transformation": "1 / (RUB per USD)",
                "rate_type": "official_reference",
                "provider_payload": {"date": record.attrib["Date"], "nominal": str(nominal), "value": str(rub_per_nominal)},
            }
            written += write_observation(connection, series_id, period_start, canonical_value, period_start, raw_payload)
            read += 1
        complete_run(connection, run_id, read, written)
        return read, written
    except Exception as error:
        fail_run(connection, run_id, error)
        raise


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--start", help="Explicit earliest date to load (YYYY-MM-DD).")
    parser.add_argument("--backfill", action="store_true", help="Load the full twenty-year chart history instead of the normal 45-day refresh window.")
    args = parser.parse_args()
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        sys.exit("DATABASE_URL must be set. See ingestion/.env.example.")
    end = date.today()
    if args.start and args.backfill:
        parser.error("Use either --start or --backfill, not both.")
    try:
        start = date.fromisoformat(args.start) if args.start else date(end.year - 20, end.month, end.day) if args.backfill else end - timedelta(days=45)
    except ValueError as error:
        parser.error(f"--start must use YYYY-MM-DD: {error}")
    if start > end:
        parser.error("--start cannot be in the future")

    with psycopg.connect(database_url) as connection:
        ecb_read, ecb_written = run_ecb(connection, start, end)
        boc_read, boc_written = run_boc(connection, start, end)
        nbu_read, nbu_written = run_nbu(connection, start, end)
        cbr_read, cbr_written = run_cbr(connection, start, end)
    print(f"ECB: {ecb_read} observations read, {ecb_written} new")
    print(f"Bank of Canada: {boc_read} observations read, {boc_written} new")
    print(f"National Bank of Ukraine: {nbu_read} observations read, {nbu_written} new")
    print(f"Bank of Russia: {cbr_read} observations read, {cbr_written} new")
    print("Iran: intentionally pending — a single official IRR rate would not represent its multiple-rate market regime.")


if __name__ == "__main__":
    main()
