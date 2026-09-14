insert into sources (slug, name, tier, source_type, base_url, license_note) values
  ('ecb-data-portal', 'ECB Data Portal', 1, 'official', 'https://data.ecb.europa.eu/', 'Official ECB SDMX data service')
on conflict (slug) do update set
  name = excluded.name, tier = excluded.tier, source_type = excluded.source_type,
  base_url = excluded.base_url, license_note = excluded.license_note;
