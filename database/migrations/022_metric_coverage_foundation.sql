-- Coverage state needs the cadence actually published by a source-series.
-- Indicators retain their canonical default cadence, while this column records
-- exceptions such as quarterly Australian CPI.
alter table source_series
  add column if not exists frequency text
  check (frequency in ('daily', 'weekly', 'monthly', 'quarterly', 'annual', 'event'));

update source_series as series
set frequency = indicators.frequency
from indicators
where indicators.id = series.indicator_id
  and series.frequency is null;

insert into sources (slug, name, tier, source_type, base_url, license_note)
values (
  'reserve-bank-australia-data',
  'Reserve Bank of Australia Statistical Tables',
  1,
  'official',
  'https://www.rba.gov.au/statistics/tables/',
  'Official RBA statistical-table CSV files. Individual observations retain the table publication date and series identifier.'
)
on conflict (slug) do update set
  name = excluded.name,
  tier = excluded.tier,
  source_type = excluded.source_type,
  base_url = excluded.base_url,
  license_note = excluded.license_note;
