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

## First source tiers

1. Official central-bank, statistical-office and ministry releases.
2. Official multilateral institutions.
3. Licensed publisher APIs, only after their usage terms are recorded.
4. Discovery feeds are candidates only; they cannot support a published claim
   without a link to the original publisher.

## AI-ready evidence pack

Each future model run receives a frozen set of observation IDs, article IDs,
event IDs and source URLs. It can create hypotheses and scenarios but never
mutate canonical facts or raw documents.

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
