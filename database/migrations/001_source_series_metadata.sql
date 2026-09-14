alter table source_series add column if not exists display_name text;
alter table source_series add column if not exists unit text;

update source_series
set display_name = case external_id
  when 'DFF' then 'Effective Federal Funds Rate'
  when 'CPIAUCSL' then 'Consumer Price Index'
  when 'UNRATE' then 'Unemployment Rate'
  when 'PAYEMS' then 'All Employees: Total Nonfarm'
  when 'GDPC1' then 'Real Gross Domestic Product'
  when 'DGS2' then '2-Year US Treasury Yield'
  when 'DGS10' then '10-Year US Treasury Yield'
  else display_name
end,
unit = case external_id
  when 'DFF' then 'percent'
  when 'CPIAUCSL' then 'index'
  when 'UNRATE' then 'percent'
  when 'PAYEMS' then 'thousands of persons'
  when 'GDPC1' then 'billions of chained dollars'
  when 'DGS2' then 'percent'
  when 'DGS10' then 'percent'
  else unit
end
where external_id in ('DFF', 'CPIAUCSL', 'UNRATE', 'PAYEMS', 'GDPC1', 'DGS2', 'DGS10');

update indicators set name = 'Policy Rate' where slug = 'policy-rate';
