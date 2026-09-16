# News evidence pipeline

News is an evidence layer for macro research. It is not a content-scraping or
article-republishing system.

## Ingestion contract

1. Poll an authorized `news_feed` or provider API.
2. Store the response item unchanged in `raw_documents`, including its source
   URL, canonical URL, publication timestamp, content hash and raw payload.
3. Normalize only the publisher-provided metadata into `news_articles`.
4. Deduplicate by canonical URL first, then by content hash.
5. Link related articles to one `news_event_cluster`; attach every affected
   country and macro indicator explicitly.
6. Record each country relationship as `direct`, `regional` or `spillover`.
   Add the actor, conflict, institution or technology entity separately from
   the country relationship.
7. Record expected market transmission independently from observed market
   reaction. A hypothesis never masquerades as a price fact.

`metadata_only` feeds must never persist publisher article body text. The UI
links to the original source. Any model-generated prose is stored separately
from the evidence it cites.

## Verification states

The Global Risk Tape keeps early signals visible rather than silently dropping
them. Its verification state is derived at read time from the immutable source
and reaction records, so it can be re-evaluated as evidence arrives:

1. `UNVERIFIED` — a single discovery or publisher intake record. Visible in
   the `SIGNALS` filter, but never sufficient for a market-moving conclusion.
2. `CORROBORATED` — at least two independent non-discovery intake sources.
3. `OFFICIAL` — at least one linked primary official source.
4. `MARKET_CONFIRMED` — a separately stored measured market reaction exists.

The states do not express whether a claim is true. They express the quality of
the evidence currently stored in the research database. A future AI briefing
must cite the underlying event and article IDs, and must not promote an
unverified signal into a conclusion.

## First source tiers

1. Official central-bank, statistical-office and ministry releases.
2. Official multilateral institutions.
3. Licensed publisher APIs, only after their usage terms are recorded.
4. Discovery feeds are candidates only; they cannot support a published claim
   without a link to the original publisher.

Alpha Vantage is a tier-3 market-news metadata source. It is useful for broad
macro, energy and technology discovery, but its provider score never makes an
event market-moving by itself. The original publisher link remains the UI
destination and future AI evidence citation. The worker passes `time_from` and
imports only a rolling seven-day window by default, so an old provider result
cannot appear as live evidence.

EIA's official feeds anchor U.S. energy observations. The rule layer marks
them direct to the United States first, then adds any named country from the
item metadata; explicit Iran, Russia–Ukraine and China-technology rules add
their documented regional and spillover relationships.

The International Atomic Energy Agency RSS feed is a tier-1 primary layer for
nuclear-safety context, including Ukraine and Iran when the publisher metadata
names them. `federal_register_risk.py` imports the Federal Register API's
metadata for Executive Orders and Bureau of Industry and Security notices. It
requires no key and is the primary U.S. policy, tariffs and export-controls
layer. Neither source is a substitute for a real-time conflict alert feed.

BBC World and Business RSS are explicitly marked `LOCAL-ONLY` in the source
registry. They supply a CNN-like international editorial layer for personal
research and are still ingested as metadata only. Before public deployment,
disable them or record BBC's required permission; do not silently carry this
source into production.

## AI-ready evidence pack

Each future model run receives a frozen set of observation IDs, article IDs,
event IDs and source URLs. It can create hypotheses and scenarios but never
mutate canonical facts or raw documents.

## Canonical event threads

`news_event_threads` is a research-facing view over immutable event clusters.
The automatic v1 method groups only same-type, country-overlapping headlines
within 72 hours and with high token similarity. Each thread keeps every linked
cluster and therefore every original publisher URL; it is never a replacement
for source evidence. Low-confidence matches intentionally remain separate.

## Global event graph

Country pages are views into a global event graph, not isolated national RSS
feeds. For example, an Iran conflict event can be directly linked to Iran,
linked as spillover to oil-sensitive economies, and linked to Brent through a
documented shipping/supply transmission. The same applies to Russia–Ukraine
events and China technology policy. `news_event_market_impacts` contains the
ex-ante relationship; `news_event_market_reactions` only contains measured
5-minute, 1-hour or 1-day moves with a source URL.

The materiality feed uses the decomposed score in `news_event_scores`:
source quality, event significance, systemic reach, freshness and—when
available—observed reaction. It is intentionally auditable rather than a
single opaque AI score.

## Research-feed policy

The working UI is deliberately narrower than the evidence archive and has two
explicit relevance tiers. Both require a 45-day window. `MARKET_MOVING` is the
strict tier:

1. geopolitics with an explicit market-transmission rule;
2. concrete policy actions, such as tariffs, sanctions, Executive Orders or
   export controls—not a speech or a political opinion;
3. China technology/export-control developments; and
4. named macro releases or rate decisions, excluding explainers.

All other metadata remains locally as auditable provenance but does not appear
in the research feed. This preserves reproducibility without allowing old
articles, routine statements or calendar-like notices to dilute the market
read.

`RESEARCH_SIGNAL` is intentionally broader: relevant geopolitical incidents,
policy statements, prospective macro growth/inflation/labour developments,
China technology developments and official energy/trade communications can
appear before a direct market impact is confirmed. It is visually labelled and
can be filtered away. Generic commentary, explainers, calendars, cultural news
and unrelated official communications remain outside both tiers.

## Scheduled economic calendar

`economic_calendar_events` is a separate, forward-looking evidence layer. A
calendar record holds the planned timestamp, importance, consensus, previous
value and later actual value. It is not converted into a news event before a
release occurs, preventing hindsight leakage in future AI briefings.

The initial authorised connector is `trading_economics_calendar.py`. It needs
a licensed `TRADING_ECONOMICS_API_KEY`; the provider supplies calendar
metadata and a link to the primary publisher. Forex Factory must not be
scraped or redistributed without written permission under its published terms.

## Discovery layer

`gdelt_discovery.py` is deliberately scoped to Trump/White House, Iran and oil,
Russia–Ukraine, and China technology. It imports only title, timestamp and the
original publisher URL. Its source score is lower than official or licensed
coverage, and it must be corroborated before it can support a published claim.
It issues one broad query per run and persists public-endpoint failures to
`ingestion_runs`; do not bypass a 429 or simulate a browser to evade it.

## Safe update order and health

Run `python3 ingestion/run_news_pipeline.py` after loading `ingestion/.env`.
It performs `RSS/provider ingest → classification → canonical threading` and
does not make a GDELT request by default. It does include a free Federal
Register primary-source check. Add `--with-gdelt` only for one intentional
discovery attempt; a 429 is recorded and does not block publisher evidence.
Country API responses expose the latest `ingestion_runs` status for every
active news source as CURRENT, DELAYED, ATTENTION or PENDING.

## News coverage matrix

`/macro` exposes the **News Coverage Matrix**. Its domain definitions live in
`data/newsCoverage.ts`; the API evaluates their requirements from the latest
`ingestion_runs`, rather than trusting a static source list. A source is
`CURRENT` only when its latest completed check is no older than 36 hours.

`LIVE` means every configured primary and discovery layer has a current check.
`PARTIAL` means the primary layer is current but an explicitly required
secondary layer is not. `GAP` means the primary layer itself is absent or
stale. This is a coverage contract, not a claim that every world event is
captured. The matrix deliberately leaves fast social signals and a dedicated
authorised maritime incident feed as gaps until a permitted source and a named
watchlist are configured.

## US economic calendar

`businessquant_calendar.py` imports the free BusinessQuant US release calendar
into `economic_calendar_events`. Its supplied dates are stored as `date_only`;
the UI must display `TIME TBC` rather than invent a release time. The provider
does not supply consensus in this integration, so only prior values appear.

The official `fomc_calendar.py` independently inserts upcoming FOMC policy
decisions at importance 5. Its timestamp is labelled `EST.` because the annual
schedule confirms dates while the monthly official calendar confirms release
time; the source URL remains attached to every record.

`bank_of_england_calendar.py` imports MPC decision dates from the official Bank
of England schedule. The source does not supply a universal precise release
time for the forward schedule, so these events remain `date_only` and the UI
shows `TIME TBC`. Confirmed and provisional dates are retained separately in
the raw provenance payload.

`ecb_calendar.py` imports the Day 2 monetary-policy meeting and press
conference dates from the official ECB calendar. Each decision is written to
the France, Germany, Italy and Spain desks independently. The schedule is
date-only, so it remains `TIME TBC` until the ECB publishes a precise release
time.

`asia_pacific_policy_calendars.py` imports future Bank of Japan Monetary Policy
Meeting end dates and Reserve Bank of Australia Monetary Policy Board meeting
end dates directly from their official schedules. Both remain `TIME TBC`: a
meeting date is not evidence of an announced decision time. The Reserve Bank
of New Zealand schedule is a separately labelled official snapshot through
February 2028 because its public page currently returns HTTP 403 to
server-to-server clients. Before that horizon expires, replace the snapshot
with an authorised machine-readable RBNZ feed or a provider licence; do not
work around the site's access controls.
