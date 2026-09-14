-- First expansion wave: two verified official central-bank RSS publishers and
-- one discovery-only global monitor. Discovery records never become a factual
-- claim without their linked original publisher.

insert into sources (slug, name, tier, source_type, base_url, license_note) values
  ('bank-of-canada-communications', 'Bank of Canada Communications', 1, 'official', 'https://www.bankofcanada.ca/', 'Official press releases and speeches; metadata-only RSS ingestion.'),
  ('reserve-bank-australia-communications', 'Reserve Bank of Australia Communications', 1, 'official', 'https://www.rba.gov.au/', 'Official media releases and speeches; metadata-only RSS ingestion.'),
  ('gdelt-discovery', 'GDELT Discovery Monitor', 4, 'news', 'https://www.gdeltproject.org/', 'Discovery only; preserve and display the original publisher URL. Never use as sole support for a published claim.')
on conflict (slug) do update set name = excluded.name, tier = excluded.tier, source_type = excluded.source_type, base_url = excluded.base_url, license_note = excluded.license_note;

insert into news_feeds (source_id, name, feed_url, content_policy)
select sources.id, feeds.name, feeds.feed_url, 'metadata_only'
from sources join (values
  ('bank-of-canada-communications', 'Bank of Canada · Press Releases', 'https://www.bankofcanada.ca/content_type/press-releases/feed/'),
  ('bank-of-canada-communications', 'Bank of Canada · Speeches & Appearances', 'https://www.bankofcanada.ca/content_type/speeches/feed/'),
  ('reserve-bank-australia-communications', 'RBA · Media Releases', 'https://www.rba.gov.au/rss/rss-cb-media-releases.xml'),
  ('reserve-bank-australia-communications', 'RBA · Speeches', 'https://www.rba.gov.au/rss/rss-cb-speeches.xml')
) as feeds(source_slug, name, feed_url) on sources.slug = feeds.source_slug
on conflict (feed_url) do update set name = excluded.name, content_policy = excluded.content_policy, active = true;
