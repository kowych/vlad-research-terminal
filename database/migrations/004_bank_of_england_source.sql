insert into sources (slug, name, tier, source_type, base_url, license_note) values
  ('bank-of-england', 'Bank of England Statistical Database', 1, 'official', 'https://www.bankofengland.co.uk/boeapps/database/', 'Official Bank of England statistical time-series database')
on conflict (slug) do update set
  name = excluded.name, tier = excluded.tier, source_type = excluded.source_type,
  base_url = excluded.base_url, license_note = excluded.license_note;
