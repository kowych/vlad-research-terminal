"""Ingest comparable, annual World Bank WDI baseline data for every covered country."""
from __future__ import annotations
import json, os, sys
import argparse
from datetime import date
from decimal import Decimal
from urllib.parse import urlencode
from urllib.request import urlopen
import psycopg

WORLD_BANK_API = "https://api.worldbank.org/v2/country"
INDICATORS = {
    "gdp-current-usd": ("NY.GDP.MKTP.CD", "GDP (current US$)", "current US dollars"),
    "gdp-growth-annual": ("NY.GDP.MKTP.KD.ZG", "GDP growth (annual %)", "percent"),
    "inflation-cpi-annual": ("FP.CPI.TOTL.ZG", "Inflation, consumer prices (annual %)", "percent"),
    "unemployment-total": ("SL.UEM.TOTL.ZS", "Unemployment, total", "percent"),
    "trade-gdp": ("NE.TRD.GNFS.ZS", "Trade (% of GDP)", "percent"),
}

def fetch(iso3_codes: list[str], indicator_code: str) -> tuple[dict, list[dict]]:
    query = urlencode({"format": "json", "per_page": 20000, "date": "1990:2026"})
    url = f"{WORLD_BANK_API}/{'/'.join([';'.join(iso3_codes), 'indicator', indicator_code])}?{query}"
    with urlopen(url, timeout=30) as response: payload = json.load(response)
    if not isinstance(payload, list) or len(payload) != 2: raise RuntimeError(f"Unexpected World Bank response for {indicator_code}")
    return payload[0], payload[1] or []

def as_of_date(metadata: dict) -> str:
    try: return date.fromisoformat(str(metadata.get("lastupdated") or "")).isoformat()
    except ValueError: return date.today().isoformat()

def run(database_url: str) -> None:
    with psycopg.connect(database_url) as connection:
        with connection.cursor() as cursor:
            cursor.execute("select iso2, iso3 from countries where active and iso3 is not null order by iso2")
            country_codes = {row[1]: row[0] for row in cursor.fetchall()}
        for indicator_slug, (external_id, display_name, unit) in INDICATORS.items():
            metadata, rows = fetch(list(country_codes), external_id)
            with connection.cursor() as cursor:
                cursor.execute("insert into ingestion_runs (source_id, status) select id, 'started' from sources where slug = 'world-bank-wdi' returning id")
                run_id = cursor.fetchone()[0]
            connection.commit()
            try:
                written = 0; vintage = as_of_date(metadata)
                with connection.cursor() as cursor:
                    for row in rows:
                        if row.get("value") is None or row.get("countryiso3code") not in country_codes: continue
                        country_iso2 = country_codes[row["countryiso3code"]]
                        cursor.execute("""insert into source_series (source_id, indicator_id, country_id, external_id, display_name, unit)
                          select sources.id, indicators.id, countries.id, %s, %s, %s from sources, indicators, countries
                          where sources.slug = 'world-bank-wdi' and indicators.slug = %s and countries.iso2 = %s
                          on conflict (source_id, country_id, external_id) do update set display_name = excluded.display_name, unit = excluded.unit returning id""", (external_id, display_name, unit, indicator_slug, country_iso2))
                        source_series_id = cursor.fetchone()[0]
                        cursor.execute("""insert into observations (source_series_id, period_start, value, as_of_date, raw_payload)
                          values (%s, %s, %s, %s, %s::jsonb) on conflict (source_series_id, period_start, as_of_date) do nothing""", (source_series_id, f"{row['date']}-01-01", Decimal(str(row["value"])), vintage, json.dumps(row)))
                        written += cursor.rowcount
                    cursor.execute("update ingestion_runs set status = 'completed', completed_at = now(), records_read = %s, records_written = %s where id = %s", (len(rows), written, run_id))
                connection.commit(); print(f"{external_id}: {written} new observations; official vintage {vintage}")
            except Exception as error:
                connection.rollback()
                with connection.cursor() as cursor: cursor.execute("update ingestion_runs set status = 'failed', completed_at = now(), error_message = %s where id = %s", (str(error), run_id))
                connection.commit(); raise

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--indicator", choices=INDICATORS.keys(), help="Load one indicator only")
    args = parser.parse_args()
    database_url = os.environ.get("DATABASE_URL")
    if not database_url: sys.exit("DATABASE_URL must be set. See ingestion/.env.example.")
    if args.indicator:
        INDICATORS = {args.indicator: INDICATORS[args.indicator]}
    run(database_url)
