insert into indicators (slug, name, category, unit, frequency) values
  ('core-cpi', 'Core Consumer Price Index', 'inflation', 'index', 'monthly'),
  ('real-gdp-growth', 'Real GDP Growth', 'growth', 'percent', 'quarterly'),
  ('sovereign-10y', '10-Year Sovereign Yield', 'market', 'percent', 'daily')
on conflict (slug) do update set name = excluded.name, category = excluded.category, unit = excluded.unit, frequency = excluded.frequency;
