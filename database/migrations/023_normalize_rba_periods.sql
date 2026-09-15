-- RBA CSV tables label observations with an end-of-period date. The canonical
-- schema keeps a start/end interval instead. This corrects the first RBA load
-- without changing its values, source vintage or raw provenance.
update observations as observation
set
  period_end = observation.period_start,
  period_start = case source_series.frequency
    when 'monthly' then date_trunc('month', observation.period_start)::date
    when 'quarterly' then date_trunc('quarter', observation.period_start)::date
    else observation.period_start
  end
from source_series
join sources on sources.id = source_series.source_id
where source_series.id = observation.source_series_id
  and sources.slug = 'reserve-bank-australia-data'
  and source_series.frequency in ('monthly', 'quarterly')
  and observation.period_end is null;
