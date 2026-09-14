insert into countries (iso2, iso3, name, capital, currency_code, wikidata_id) values
  ('US', 'USA', 'United States', 'Washington, D.C.', 'USD', 'Q30'),
  ('IR', 'IRN', 'Iran', 'Tehran', 'IRR', 'Q794'),
  ('GB', 'GBR', 'United Kingdom', 'London', 'GBP', 'Q145'),
  ('FR', 'FRA', 'France', 'Paris', 'EUR', 'Q142'),
  ('DE', 'DEU', 'Germany', 'Berlin', 'EUR', 'Q183'),
  ('UA', 'UKR', 'Ukraine', 'Kyiv', 'UAH', 'Q212'),
  ('RU', 'RUS', 'Russia', 'Moscow', 'RUB', 'Q159'),
  ('AU', 'AUS', 'Australia', 'Canberra', 'AUD', 'Q408'),
  ('CA', 'CAN', 'Canada', 'Ottawa', 'CAD', 'Q16'),
  ('NZ', 'NZL', 'New Zealand', 'Wellington', 'NZD', 'Q664'),
  ('CN', 'CHN', 'China', 'Beijing', 'CNY', 'Q148'),
  ('JP', 'JPN', 'Japan', 'Tokyo', 'JPY', 'Q17'),
  ('IT', 'ITA', 'Italy', 'Rome', 'EUR', 'Q38'),
  ('ES', 'ESP', 'Spain', 'Madrid', 'EUR', 'Q29'),
  ('CH', 'CHE', 'Switzerland', 'Bern', 'CHF', 'Q39'),
  ('NO', 'NOR', 'Norway', 'Oslo', 'NOK', 'Q20'),
  ('SE', 'SWE', 'Sweden', 'Stockholm', 'SEK', 'Q34'),
  ('TR', 'TUR', 'Turkey', 'Ankara', 'TRY', 'Q43'),
  ('IN', 'IND', 'India', 'New Delhi', 'INR', 'Q668'),
  ('KR', 'KOR', 'South Korea', 'Seoul', 'KRW', 'Q884'),
  ('PL', 'POL', 'Poland', 'Warsaw', 'PLN', 'Q36')
on conflict (iso2) do update set
  iso3 = excluded.iso3, name = excluded.name, capital = excluded.capital,
  currency_code = excluded.currency_code, wikidata_id = excluded.wikidata_id,
  updated_at = now();

insert into sources (slug, name, tier, source_type, base_url, license_note) values
  ('fred', 'FRED / ALFRED', 1, 'official', 'https://fred.stlouisfed.org/', 'Federal Reserve Bank of St. Louis data service'),
  ('boj', 'Bank of Japan Time-Series Data Search', 1, 'official', 'https://www.stat-search.boj.or.jp/', 'Official Bank of Japan time-series API'),
  ('bank-of-england', 'Bank of England Statistical Database', 1, 'official', 'https://www.bankofengland.co.uk/boeapps/database/', 'Official Bank of England statistical time-series database'),
  ('ecb-data-portal', 'ECB Data Portal', 1, 'official', 'https://data.ecb.europa.eu/', 'Official ECB SDMX data service'),
  ('federal-reserve-board', 'Board of Governors of the Federal Reserve System', 1, 'official', 'https://www.federalreserve.gov/', 'Official Federal Reserve Board communications'),
  ('ecb-communications', 'European Central Bank Communications', 1, 'official', 'https://www.ecb.europa.eu/', 'Official ECB press and statistical releases'),
  ('bank-of-canada-communications', 'Bank of Canada Communications', 1, 'official', 'https://www.bankofcanada.ca/', 'Official press releases and speeches; metadata-only RSS ingestion.'),
  ('reserve-bank-australia-communications', 'Reserve Bank of Australia Communications', 1, 'official', 'https://www.rba.gov.au/', 'Official media releases and speeches; metadata-only RSS ingestion.'),
  ('gdelt-discovery', 'GDELT Discovery Monitor', 4, 'news', 'https://www.gdeltproject.org/', 'Discovery only; preserve and display the original publisher URL. Never use as sole support for a published claim.'),
  ('trading-economics-calendar', 'Trading Economics Economic Calendar', 3, 'market', 'https://api.tradingeconomics.com/', 'Licensed API required; preserve the linked official source where supplied.'),
  ('wikidata', 'Wikidata', 4, 'bootstrap', 'https://www.wikidata.org/', 'CC0; structural seed facts only'),
  ('world-bank-wdi', 'World Bank World Development Indicators', 2, 'international', 'https://api.worldbank.org/', 'Cross-country structural series'),
  ('imf-sdmx', 'IMF SDMX', 2, 'international', 'https://data.imf.org/', 'Cross-country macroeconomic series'),
  ('gdelt', 'GDELT', 4, 'news', 'https://www.gdeltproject.org/', 'Discovery only; preserve original publisher URL')
on conflict (slug) do update set name = excluded.name, tier = excluded.tier, source_type = excluded.source_type, base_url = excluded.base_url, license_note = excluded.license_note;

insert into news_feeds (source_id, name, feed_url, content_policy)
select sources.id, feeds.name, feeds.feed_url, 'metadata_only'
from sources join (values
  ('federal-reserve-board', 'Federal Reserve Board · All Press Releases', 'https://www.federalreserve.gov/feeds/press_all.xml'),
  ('ecb-communications', 'ECB · Press Releases', 'https://www.ecb.europa.eu/rss/press.html'),
  ('ecb-communications', 'ECB · Statistical Press Releases', 'https://www.ecb.europa.eu/rss/statpress.html')
  ,('bank-of-canada-communications', 'Bank of Canada · Press Releases', 'https://www.bankofcanada.ca/content_type/press-releases/feed/')
  ,('bank-of-canada-communications', 'Bank of Canada · Speeches & Appearances', 'https://www.bankofcanada.ca/content_type/speeches/feed/')
  ,('reserve-bank-australia-communications', 'RBA · Media Releases', 'https://www.rba.gov.au/rss/rss-cb-media-releases.xml')
  ,('reserve-bank-australia-communications', 'RBA · Speeches', 'https://www.rba.gov.au/rss/rss-cb-speeches.xml')
) as feeds(source_slug, name, feed_url) on sources.slug = feeds.source_slug
on conflict (feed_url) do update set name = excluded.name, content_policy = excluded.content_policy;

-- Canonical market vocabulary. It is deliberately independent of a pricing
-- vendor, so provider tickers can be added later without changing events.
insert into market_instruments (slug, name, asset_class, quote_unit) values
  ('brent-crude', 'Brent crude oil', 'commodity', 'USD/barrel'),
  ('wti-crude', 'WTI crude oil', 'commodity', 'USD/barrel'),
  ('ttf-natural-gas', 'TTF natural gas', 'commodity', 'EUR/MWh'),
  ('eur-usd', 'EUR / USD', 'fx', 'USD'),
  ('usd-jpy', 'USD / JPY', 'fx', 'JPY'),
  ('usd-cny', 'USD / CNY', 'fx', 'CNY'),
  ('us-10y', 'US Treasury 10-year yield', 'rates', '%'),
  ('bund-10y', 'German Bund 10-year yield', 'rates', '%'),
  ('msci-china', 'MSCI China', 'equity', 'index'),
  ('semiconductor-index', 'Global semiconductor index', 'equity', 'index')
on conflict (slug) do update set name = excluded.name, asset_class = excluded.asset_class, quote_unit = excluded.quote_unit;

insert into indicators (slug, name, category, unit, frequency) values
  ('policy-rate', 'Policy Rate', 'policy', 'percent', 'daily'),
  ('cpi', 'Consumer Price Index', 'inflation', 'index', 'monthly'),
  ('core-cpi', 'Core Consumer Price Index', 'inflation', 'index', 'monthly'),
  ('unemployment-rate', 'Unemployment Rate', 'labour', 'percent', 'monthly'),
  ('nonfarm-payrolls', 'All Employees: Total Nonfarm', 'labour', 'thousands of persons', 'monthly'),
  ('real-gdp', 'Real Gross Domestic Product', 'growth', 'billions of chained dollars', 'quarterly'),
  ('real-gdp-growth', 'Real GDP Growth', 'growth', 'percent', 'quarterly'),
  ('treasury-2y', '2-Year Treasury Constant Maturity Rate', 'market', 'percent', 'daily'),
  ('treasury-10y', '10-Year Treasury Constant Maturity Rate', 'market', 'percent', 'daily'),
  ('sovereign-10y', '10-Year Sovereign Yield', 'market', 'percent', 'daily'),
  ('gdp-current-usd', 'GDP (current US$)', 'growth', 'current US dollars', 'annual'),
  ('gdp-growth-annual', 'GDP growth (annual %)', 'growth', 'percent', 'annual'),
  ('inflation-cpi-annual', 'Inflation, consumer prices (annual %)', 'inflation', 'percent', 'annual'),
  ('unemployment-total', 'Unemployment, total (% of total labor force)', 'labour', 'percent', 'annual'),
  ('trade-gdp', 'Trade (% of GDP)', 'external', 'percent', 'annual')
on conflict (slug) do update set name = excluded.name, category = excluded.category, unit = excluded.unit, frequency = excluded.frequency;
