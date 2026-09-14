insert into countries (iso2, iso3, name, capital, currency_code, wikidata_id) values
  ('IT', 'ITA', 'Italy', 'Rome', 'EUR', 'Q38'),
  ('ES', 'ESP', 'Spain', 'Madrid', 'EUR', 'Q29'),
  ('CH', 'CHE', 'Switzerland', 'Bern', 'CHF', 'Q39'),
  ('NO', 'NOR', 'Norway', 'Oslo', 'NOK', 'Q20'),
  ('SE', 'SWE', 'Sweden', 'Stockholm', 'SEK', 'Q34'),
  ('TR', 'TUR', 'Turkey', 'Ankara', 'TRY', 'Q43'),
  ('IN', 'IND', 'India', 'New Delhi', 'INR', 'Q668'),
  ('KR', 'KOR', 'South Korea', 'Seoul', 'KRW', 'Q884')
on conflict (iso2) do update set
  iso3 = excluded.iso3, name = excluded.name, capital = excluded.capital,
  currency_code = excluded.currency_code, wikidata_id = excluded.wikidata_id,
  updated_at = now();
