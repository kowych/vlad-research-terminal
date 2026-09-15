-- Alpha Vantage supplies provider-authorised market-news metadata. It is not
-- treated as an official source, and every item retains the publisher URL.
insert into sources (slug, name, tier, source_type, base_url, license_note)
values (
  'alpha-vantage-market-news',
  'Alpha Vantage Market News & Sentiment',
  3,
  'market',
  'https://www.alphavantage.co/',
  'Provider-authorised metadata only; retain the original publisher URL and do not store article body text.'
)
on conflict (slug) do update set
  name = excluded.name,
  tier = excluded.tier,
  source_type = excluded.source_type,
  base_url = excluded.base_url,
  license_note = excluded.license_note;
