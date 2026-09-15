-- EIA publishes these feeds itself and explicitly describes them as timely
-- energy articles and press releases.  They provide a free primary-source
-- layer for oil, gas, supply and energy-security narratives.
insert into sources (slug, name, tier, source_type, base_url, license_note)
values (
  'us-eia-energy',
  'U.S. Energy Information Administration',
  1,
  'official',
  'https://www.eia.gov/',
  'Official EIA RSS metadata only; preserve original links and do not fetch article pages.'
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
  ('us-eia-energy', 'EIA · Today in Energy', 'https://www.eia.gov/rss/todayinenergy.xml'),
  ('us-eia-energy', 'EIA · Press Releases', 'https://www.eia.gov/rss/press_rss.xml')
) as feeds(source_slug, name, feed_url) on sources.slug = feeds.source_slug
on conflict (feed_url) do update set
  name = excluded.name,
  content_policy = excluded.content_policy,
  active = true;
