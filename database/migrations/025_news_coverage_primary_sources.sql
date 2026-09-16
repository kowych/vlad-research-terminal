-- Free primary-source expansion for the market-risk evidence layer.
-- IAEA supplies nuclear-safety updates; Federal Register is the official U.S.
-- publication channel for executive actions and BIS export-control notices.
insert into sources (slug, name, tier, source_type, base_url, license_note)
values
  (
    'iaea-news',
    'International Atomic Energy Agency',
    1,
    'official',
    'https://www.iaea.org/',
    'Official IAEA RSS metadata only; retain the original item URL and do not fetch article pages.'
  ),
  (
    'federal-register-risk',
    'Federal Register · U.S. Policy & Export Controls',
    1,
    'official',
    'https://www.federalregister.gov/',
    'Official Federal Register API metadata for Executive Orders and Bureau of Industry and Security notices; public API, no key required.'
  )
on conflict (slug) do update set
  name = excluded.name,
  tier = excluded.tier,
  source_type = excluded.source_type,
  base_url = excluded.base_url,
  license_note = excluded.license_note,
  active = true;

insert into news_feeds (source_id, name, feed_url, content_policy)
select id, 'IAEA · Top Stories', 'https://www.iaea.org/feeds/news', 'metadata_only'
from sources
where slug = 'iaea-news'
on conflict (feed_url) do update set
  name = excluded.name,
  content_policy = excluded.content_policy,
  active = true;
