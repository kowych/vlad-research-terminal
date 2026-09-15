-- BBC RSS is enabled for this local, personal research environment only.
-- Before public or commercial deployment, obtain BBC permission and update the
-- source license note / active status accordingly.
insert into sources (slug, name, tier, source_type, base_url, license_note)
values (
  'bbc-news-local',
  'BBC News · World & Business',
  3,
  'news',
  'https://www.bbc.co.uk/news/',
  'LOCAL-ONLY: publisher RSS metadata (headline, supplied summary and original URL). Obtain BBC permission before any public or commercial deployment.'
)
on conflict (slug) do update set
  name = excluded.name,
  tier = excluded.tier,
  source_type = excluded.source_type,
  base_url = excluded.base_url,
  license_note = excluded.license_note;

insert into news_feeds (source_id, name, feed_url, content_policy)
select sources.id, feeds.name, feeds.feed_url, 'metadata_only'
from sources join (values
  ('bbc-news-local', 'BBC News · World', 'https://feeds.bbci.co.uk/news/world/rss.xml'),
  ('bbc-news-local', 'BBC News · Business', 'https://feeds.bbci.co.uk/news/business/rss.xml')
) as feeds(source_slug, name, feed_url) on sources.slug = feeds.source_slug
on conflict (feed_url) do update set
  name = excluded.name,
  content_policy = excluded.content_policy,
  active = true;
