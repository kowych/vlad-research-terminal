insert into sources (slug, name, tier, source_type, base_url, license_note)
values ('eu-council-communications', 'Council of the European Union Communications', 1, 'official', 'https://www.consilium.europa.eu/', 'Official Council and European Council press releases; metadata-only RSS ingestion.')
on conflict (slug) do update set name = excluded.name, tier = excluded.tier, source_type = excluded.source_type, base_url = excluded.base_url, license_note = excluded.license_note;

insert into news_feeds (source_id, name, feed_url, content_policy)
select id, 'Council of the EU · Press Releases', 'https://www.consilium.europa.eu/en/rss/pressreleases.ashx', 'metadata_only'
from sources where slug = 'eu-council-communications'
on conflict (feed_url) do update set name = excluded.name, content_policy = excluded.content_policy, active = true;
