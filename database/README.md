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

## Next step

The repository now includes a local PostgreSQL service in `docker-compose.yml` and a FRED/ALFRED worker at `ingestion/fred_us.py`.

```bash
docker compose up -d postgres
python3 -m venv .venv
.venv/bin/pip install -r ingestion/requirements.txt
set -a; source ingestion/.env; set +a
.venv/bin/python ingestion/fred_us.py
```

The worker loads US policy rate, CPI, unemployment, payrolls, real GDP and 2Y/10Y Treasury yields. The same framework also supports Japan (`--country JP`) with Bank of Japan central-bank rate, CPI, unemployment, real GDP and a 10Y government-bond yield. It requires a personal FRED API key and does not run until the key is supplied.

Normal runs ingest the latest official vintage. A separate, paginated historical-vintage backfill will be added before using the data to evaluate historical research decisions; FRED caps a single response at 2,000 vintages.

`ingestion/boj_japan.py` is a separate primary-source connector for the Bank of Japan API. It currently imports the uncollateralized overnight call rate; other Japan indicators must meet the same source and freshness standard before they are published.

`ingestion/world_bank_core.py` imports comparable annual WDI baseline data for every country in the registry: GDP level, GDP growth, inflation, unemployment and trade exposure. These are useful structural signals, but are intentionally labelled `PARTIAL DATA` until high-frequency primary-source connectors are added.

`ingestion/bank_of_england_uk.py` imports the official UK Bank Rate. `ingestion/ecb_euro_area.py` imports the ECB main refinancing operations rate for France and Germany. Both store raw official observations and the date the official database was checked; forward-dated ECB observations are preserved for audit but excluded from the current desk display.
