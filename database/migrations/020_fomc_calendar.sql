insert into sources (slug, name, tier, source_type, base_url, license_note)
values (
  'federal-reserve-fomc-calendar',
  'Federal Reserve · FOMC Calendar',
  1,
  'official',
  'https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm',
  'Official FOMC meeting schedule and policy-decision calendar.'
)
on conflict (slug) do update set
  name = excluded.name,
  tier = excluded.tier,
  source_type = excluded.source_type,
  base_url = excluded.base_url,
  license_note = excluded.license_note;
