insert into countries (iso2, iso3, name, capital, currency_code, wikidata_id) values
  ('PL', 'POL', 'Poland', 'Warsaw', 'PLN', 'Q36')
on conflict (iso2) do update set
  iso3 = excluded.iso3, name = excluded.name, capital = excluded.capital,
  currency_code = excluded.currency_code, wikidata_id = excluded.wikidata_id,
  updated_at = now();
