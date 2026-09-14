insert into sources (slug, name, tier, source_type, base_url, license_note) values
  ('boj', 'Bank of Japan Time-Series Data Search', 1, 'official', 'https://www.stat-search.boj.or.jp/', 'Official Bank of Japan time-series API')
on conflict (slug) do update set
  name = excluded.name, tier = excluded.tier, source_type = excluded.source_type,
  base_url = excluded.base_url, license_note = excluded.license_note;
