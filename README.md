# Muklanovich Research

An independent research desk for macroeconomics, markets and quantitative analysis.

## Local development

```bash
npm ci
npm run dev
```

Open the local URL printed by Next.js.

## Publishing content

The first release uses a typed local catalogue at `lib/content.ts`. Add an entry to one of these arrays:

- `researchPosts` for a long-form paper;
- `dailyNotes` for a market journal entry;
- `positions` for a public position with risk and invalidation, without P/L.

Posts are then shown in their archive automatically. A research entry also receives a static page at `/research/[slug]`; daily entries appear at `/daily/[slug]`.

### Research template

```ts
{
  slug: "descriptive-url-slug",
  title: "Paper title",
  summary: "One-sentence abstract.",
  category: "MACRO / FX",
  publishedAt: "14 SEP 2026",
  status: "ACTIVE",
  thesis: "The central view and reasoning.",
  catalysts: ["What can move the thesis", "A second catalyst"],
  invalidation: "What would make the thesis wrong.",
}
```

This is intentionally local and dependency-free. Once publishing needs exceed a compact catalogue, the presentation layer can be kept while the source moves to MDX or a CMS.

## Macro data platform

The country registry lives in `data/countries.ts` and drives the interactive globe, country routes and coverage status. PostgreSQL is the system of record for macro observations, events and the forward calendar; the schema and source rules are in `database/`.

```bash
docker compose up -d postgres
cp .env.local.example .env.local
python3 -m venv .venv
.venv/bin/pip install -r ingestion/requirements.txt
cp ingestion/.env.example ingestion/.env
```

`DATABASE_URL` is server-only; do not use a `NEXT_PUBLIC_` prefix. The United States, Australia, France, Germany, Italy and Spain currently meet the complete six-metric live standard. The remaining desks are intentionally shown as partial, delayed or missing in the **Six-Metric Coverage** dashboard at `/macro`; each status includes its source, cadence, reference period and reason. No annual World Bank baseline is presented as a current macro release.

For an existing local database, apply each new SQL migration through the
PostgreSQL container before running its corresponding worker. For the current
news coverage expansion:

```bash
docker compose exec -T postgres psql -U research -d muklanovich_research \
  -v ON_ERROR_STOP=1 -f /dev/stdin < database/migrations/025_news_coverage_primary_sources.sql
docker compose exec -T postgres psql -U research -d muklanovich_research \
  -v ON_ERROR_STOP=1 -f /dev/stdin < database/migrations/026_market_moving_news_filter.sql
docker compose exec -T postgres psql -U research -d muklanovich_research \
  -v ON_ERROR_STOP=1 -f /dev/stdin < database/migrations/027_research_signal_news_feed.sql
```

## Data updates

Run the source-specific macro workers when their official data updates. For news and the US calendar, use the safe orchestration command below after setting the connector keys in `ingestion/.env`:

```bash
set -a; source ingestion/.env; set +a
.venv/bin/python ingestion/run_news_pipeline.py
```

The runner now includes two free primary sources: IAEA RSS and Federal
Register Executive Order/BIS export-control metadata. The `/macro` **News
Coverage Matrix** evaluates current source checks by risk domain; it exposes
partial coverage and gaps rather than treating a configured source as live.

The runner always preserves source health. Optional free-tier providers such as Alpha Vantage and BusinessQuant cannot block the official-feed, classification, threading, FOMC or Bank of England calendar steps.

For the high-frequency macro desks, run the source workers separately:

```bash
set -a; source ingestion/.env; set +a
.venv/bin/python ingestion/fred_us.py --country US
.venv/bin/python ingestion/rba_macro.py
.venv/bin/python ingestion/ecb_euro_area.py
.venv/bin/python ingestion/eurostat_country_metrics.py
```

The RBA, ECB and Eurostat workers consume public official data; they require only `DATABASE_URL`. The FRED worker additionally requires `FRED_API_KEY`.

## Verification

```bash
npx tsc --noEmit
npm run lint
npm run build -- --webpack
git diff --check
```
