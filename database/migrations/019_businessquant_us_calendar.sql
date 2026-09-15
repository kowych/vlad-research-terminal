-- Free US-only forward calendar. Provider records remain separate from news
-- events so a future release can never leak into an as-of briefing.
insert into sources (slug, name, tier, source_type, base_url, license_note)
values (
  'businessquant-us-calendar',
  'BusinessQuant US Economic Calendar',
  3,
  'market',
  'https://data.businessquant.com/',
  'Provider-authorised US calendar metadata; preserve provider provenance and do not infer release times when only a date is supplied.'
)
on conflict (slug) do update set
  name = excluded.name,
  tier = excluded.tier,
  source_type = excluded.source_type,
  base_url = excluded.base_url,
  license_note = excluded.license_note;
