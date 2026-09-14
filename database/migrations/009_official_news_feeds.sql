insert into sources (slug, name, tier, source_type, base_url, license_note) values
  ('federal-reserve-board', 'Board of Governors of the Federal Reserve System', 1, 'official', 'https://www.federalreserve.gov/', 'Official Federal Reserve Board communications'),
  ('ecb-communications', 'European Central Bank Communications', 1, 'official', 'https://www.ecb.europa.eu/', 'Official ECB press and statistical releases')
on conflict (slug) do update set
  name = excluded.name, tier = excluded.tier, source_type = excluded.source_type,
  base_url = excluded.base_url, license_note = excluded.license_note;

insert into news_feeds (source_id, name, feed_url, content_policy)
select sources.id, feeds.name, feeds.feed_url, 'metadata_only'
from sources join (values
  ('federal-reserve-board', 'Federal Reserve Board · All Press Releases', 'https://www.federalreserve.gov/feeds/press_all.xml'),
  ('ecb-communications', 'ECB · Press Releases', 'https://www.ecb.europa.eu/rss/press.html'),
  ('ecb-communications', 'ECB · Statistical Press Releases', 'https://www.ecb.europa.eu/rss/statpress.html')
) as feeds(source_slug, name, feed_url) on sources.slug = feeds.source_slug
on conflict (feed_url) do update set name = excluded.name, content_policy = excluded.content_policy;
