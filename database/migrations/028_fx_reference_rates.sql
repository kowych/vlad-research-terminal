-- Daily reference FX rates are stored in one canonical unit: US dollars per
-- one unit of local currency. The original provider quote and the conversion
-- formula remain in observations.raw_payload so the calculated value is fully
-- reproducible for research and future model use.
insert into indicators (slug, name, category, unit, frequency)
values ('fx-usd', 'Exchange Rate vs US Dollar', 'market', 'USD per local currency', 'daily')
on conflict (slug) do update set
  name = excluded.name,
  category = excluded.category,
  unit = excluded.unit,
  frequency = excluded.frequency;

insert into sources (slug, name, tier, source_type, base_url, license_note) values
  (
    'bank-of-canada-valet-fx',
    'Bank of Canada Valet · Daily FX Rates',
    1,
    'official',
    'https://www.bankofcanada.ca/valet/docs/',
    'Public daily indicative reference rates. Raw CAD quotations and the USD cross-rate calculation are retained per observation.'
  ),
  (
    'national-bank-ukraine-fx',
    'National Bank of Ukraine · Official FX Rate',
    1,
    'official',
    'https://bank.gov.ua/en/markets/exchangerates',
    'Official UAH/USD reference rate. It is labelled as a reference rate, not an executable market quote.'
  ),
  (
    'bank-of-russia-fx',
    'Bank of Russia · Official FX Rate',
    1,
    'official',
    'https://www.cbr.ru/eng/currency_base/daily/',
    'Official RUB/USD reference rate. It is labelled as a reference rate, not an executable market quote.'
  )
on conflict (slug) do update set
  name = excluded.name,
  tier = excluded.tier,
  source_type = excluded.source_type,
  base_url = excluded.base_url,
  license_note = excluded.license_note;
