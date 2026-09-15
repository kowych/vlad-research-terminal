-- Official forward policy calendars for the Asia-Pacific desks. These are
-- deliberately separate from news/communications sources: meeting schedules
-- are forward-looking evidence and must retain their own provenance.
insert into sources (slug, name, tier, source_type, base_url, license_note)
values
  (
    'bank-of-japan-policy-calendar',
    'Bank of Japan · Monetary Policy Meeting Calendar',
    1,
    'official',
    'https://www.boj.or.jp/en/mopo/mpmsche_minu/index.htm',
    'Official BOJ Monetary Policy Meeting schedule. Meeting end date is recorded; do not infer a release time when BOJ has not confirmed one.'
  ),
  (
    'reserve-bank-australia-policy-calendar',
    'Reserve Bank of Australia · Monetary Policy Board Calendar',
    1,
    'official',
    'https://www.rba.gov.au/schedules-events/board-meeting-schedules.html',
    'Official RBA Monetary Policy Board meeting schedule. Meeting end date is recorded; do not infer a decision time from the schedule alone.'
  ),
  (
    'reserve-bank-new-zealand-policy-calendar',
    'Reserve Bank of New Zealand · OCR Decision Calendar',
    1,
    'official',
    'https://www.rbnz.govt.nz/news-and-events/how-we-release-information/ocr-decision-dates-and-financial-stability-report-dates-to-feb-2028',
    'Official RBNZ OCR decision schedule. Current bootstrap dates are captured from the public schedule; refresh against the source before its published horizon expires.'
  )
on conflict (slug) do update set
  name = excluded.name,
  tier = excluded.tier,
  source_type = excluded.source_type,
  base_url = excluded.base_url,
  license_note = excluded.license_note;
