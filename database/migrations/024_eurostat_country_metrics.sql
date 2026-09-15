-- Free official European statistics for the next priority coverage wave.
insert into sources (slug, name, tier, source_type, base_url, license_note)
values (
  'eurostat-data',
  'Eurostat Data API',
  1,
  'official',
  'https://ec.europa.eu/eurostat/api/dissemination/',
  'Official European statistics API. National observations retain dataset, query and Eurostat update vintage.'
)
on conflict (slug) do update set
  name = excluded.name,
  tier = excluded.tier,
  source_type = excluded.source_type,
  base_url = excluded.base_url,
  license_note = excluded.license_note;
