# Data platform

`schema.sql` is the canonical PostgreSQL schema for the Macro product. It is deliberately independent from the Next.js application so that ingestion can run in Python workers now and a hosted API later.

## Design choices

- PostgreSQL is the source of truth; it provides relational integrity, JSON for evolving country profiles, and a clean path to time-series extensions later.
- Raw observations are immutable and vintage-aware. Never replace a released figure: insert a new observation with its `as_of_date`.
- Every event must preserve its original URL and source. AI summaries contain an evidence payload and a prompt/model version.
- Redis is optional and only caches display/API results. It must never hold the only copy of market or macro data.

## Source priority

1. Official statistical offices and central banks.
2. International institutions (IMF, World Bank, BIS, OECD where applicable).
3. Licensed market-data providers.
4. News discovery feeds; a material claim must link to the original publisher.
5. Wikidata only seeds attributable structural facts and never supersedes an official source.

## Local setup

The repository now includes a local PostgreSQL service in `docker-compose.yml` and a FRED/ALFRED worker at `ingestion/fred_us.py`.

```bash
docker compose up -d postgres
python3 -m venv .venv
.venv/bin/pip install -r ingestion/requirements.txt
set -a; source ingestion/.env; set +a
.venv/bin/python ingestion/fred_us.py
```

The FRED worker loads US policy rate, headline and core CPI, unemployment, payrolls, real GDP, real GDP growth and 2Y/10Y Treasury yields. It requires a personal FRED API key and does not run until the key is supplied.

Normal runs ingest the latest official vintage. A separate, paginated historical-vintage backfill will be added before using the data to evaluate historical research decisions; FRED caps a single response at 2,000 vintages.

`ingestion/boj_japan.py` is a separate primary-source connector for the Bank of Japan API. It currently imports the uncollateralized overnight call rate; Japan is therefore published as `PARTIAL DATA`, not as a live complete desk.

`ingestion/world_bank_core.py` imports comparable annual WDI baseline data for every country in the registry: GDP level, GDP growth, inflation, unemployment and trade exposure. These are useful structural signals, but are intentionally labelled `PARTIAL DATA` until high-frequency primary-source connectors are added.

`ingestion/bank_of_england_uk.py` imports the official UK Bank Rate. `ingestion/ecb_euro_area.py` imports the ECB main refinancing operations rate for France, Germany, Italy and Spain. Both store raw official observations and the date the official database was checked; forward-dated ECB observations are preserved for audit but excluded from the current desk display.

`ingestion/rba_macro.py` imports Australia's six desk metrics from public Reserve Bank of Australia statistical-table CSV files: cash-rate target, headline CPI, trimmed-mean inflation, unemployment, real GDP growth and the 10-year government-bond yield. It stores the RBA series identifier, table URL, reporting interval and table publication date with every observation.

`ingestion/eurostat_country_metrics.py` imports current HICP headline/core inflation, seasonally adjusted unemployment, real GDP growth and 10-year Maastricht-criterion bond yields for France, Germany, Italy, Spain and Poland from the official Eurostat API. Together with the official ECB policy-rate connector, this completes all six metrics for France, Germany, Italy and Spain. Poland remains partial until an official NBP policy-rate connector is added.

## Coverage contract

`data/metrics.ts` defines the six desk metrics and their live-data contract: approved source types, valid publication cadence and maximum reference-period age. `GET /api/coverage` evaluates every country against that contract and `/macro` displays the result.

- `LIVE`: approved source, allowed cadence, and a recent enough reference period.
- `DELAYED`: source and cadence are suitable, but the latest reference period is too old.
- `PARTIAL`: a lower-frequency or otherwise non-live fallback exists.
- `MISSING`: no connector has produced an observation for the metric.

This is an operational quality gate for future model briefs: an inference may cite partial history, but it must never treat it as current coverage.
