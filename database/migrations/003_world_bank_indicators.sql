insert into indicators (slug, name, category, unit, frequency) values
  ('gdp-current-usd', 'GDP (current US$)', 'growth', 'current US dollars', 'annual'),
  ('gdp-growth-annual', 'GDP growth (annual %)', 'growth', 'percent', 'annual'),
  ('inflation-cpi-annual', 'Inflation, consumer prices (annual %)', 'inflation', 'percent', 'annual'),
  ('unemployment-total', 'Unemployment, total (% of total labor force)', 'labour', 'percent', 'annual'),
  ('trade-gdp', 'Trade (% of GDP)', 'external', 'percent', 'annual')
on conflict (slug) do update set name = excluded.name, category = excluded.category, unit = excluded.unit, frequency = excluded.frequency;
