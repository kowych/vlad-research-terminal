import { query } from "@/lib/database";
import { countries } from "@/data/countries";
import type { CalendarEvent, EventRelevance, EventVerification, MacroDesk, MacroEvent, MacroPoint, MacroSeries, NewsSourceHealth } from "@/lib/macro";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

type SeriesRow = { slug: string; name: string; unit: string; frequency: "daily" | "weekly" | "monthly" | "quarterly" | "annual" | "event"; source_name: string; period_start: string; period_end: string | null; value: string; as_of_date: string; ingested_at: string };
type EventRow = { id: string; title: string; event_type: string; materiality: number; total_score: string | null; impact_scope: "direct" | "regional" | "spillover"; occurred_at: string; source_name: string; original_url: string; indicators: string[] | null; source_count: number; verification: EventVerification; relevance: EventRelevance };
type CalendarRow = { id: string; title: string; category: string | null; scheduled_at: string; timing_precision: "exact" | "estimated" | "date_only"; importance: number; forecast_text: string | null; previous_text: string | null; currency_code: string | null; source_name: string | null; source_url: string | null };
type CalendarSourceRow = { name: string };
type NewsHealthRow = { slug: string; name: string; status: "completed" | "failed" | null; completed_at: string | null; records_written: number | null; error_message: string | null };

const historyLimits: Record<string, number> = {
  "policy-rate": 2_600, cpi: 180, "core-cpi": 180, "unemployment-rate": 180, "nonfarm-payrolls": 180,
  "real-gdp": 80, "real-gdp-growth": 80, "treasury-2y": 2_600, "treasury-10y": 2_600, "sovereign-10y": 2_600,
};

function displayValue(row: SeriesRow): number {
  // World Bank stores nominal GDP in absolute USD. Keep the canonical value in
  // PostgreSQL and only convert the API presentation layer to billions.
  return row.slug === "gdp-current-usd" ? Number(row.value) / 1_000_000_000 : Number(row.value);
}

function toPoint(row: SeriesRow): MacroPoint { return { date: row.period_start, value: displayValue(row) }; }

function freshness(row: SeriesRow): MacroSeries["freshness"] {
  if (row.frequency === "annual") return "ANNUAL BASELINE";
  if (row.slug === "policy-rate") {
    const sourceCheckAgeInDays = (Date.now() - Date.parse(`${row.as_of_date}T00:00:00Z`)) / 86_400_000;
    return sourceCheckAgeInDays <= 30 ? "CURRENT" : "DELAYED";
  }
  const referencePeriod = row.period_end ?? row.period_start;
  const ageInDays = (Date.now() - Date.parse(`${referencePeriod}T00:00:00Z`)) / 86_400_000;
  const maximumAge = { daily: 10, weekly: 21, monthly: 62, quarterly: 160, event: 7 }[row.frequency];
  return ageInDays <= maximumAge ? "CURRENT" : "DELAYED";
}

function buildRegime(series: MacroSeries[]): Pick<MacroDesk, "regime" | "rationale"> {
  const bySlug = new Map(series.map((item) => [item.slug, item]));
  const inflation = bySlug.get("cpi")?.change ?? bySlug.get("inflation-cpi-annual")?.latest.value;
  const unemployment = bySlug.get("unemployment-rate")?.latest.value ?? bySlug.get("unemployment-total")?.latest.value;
  const policyRate = bySlug.get("policy-rate")?.latest.value;
  if (inflation !== undefined && policyRate !== undefined && inflation > policyRate) return { regime: "INFLATION PRESSURE", rationale: "The available inflation measure is above the available policy-rate measure." };
  if (unemployment !== undefined && unemployment > 5) return { regime: "LABOUR-MARKET STRESS", rationale: "The unemployment rate is above the current 5% monitoring threshold." };
  return { regime: "MONITORING", rationale: "A rules-based provisional label; it will be expanded with documented scenario logic." };
}

function toNewsHealth(row: NewsHealthRow): NewsSourceHealth {
  if (!row.status) return { slug: row.slug, name: row.name, status: "PENDING" };
  if (row.status === "failed") return { slug: row.slug, name: row.name, status: "ATTENTION", checkedAt: row.completed_at ?? undefined, error: row.error_message ?? undefined };
  const ageHours = row.completed_at ? (Date.now() - Date.parse(row.completed_at)) / 3_600_000 : Number.POSITIVE_INFINITY;
  return { slug: row.slug, name: row.name, status: ageHours <= 36 ? "CURRENT" : "DELAYED", checkedAt: row.completed_at ?? undefined, recordsWritten: row.records_written ?? undefined };
}

export async function GET(_request: Request, context: RouteContext<"/api/macro/[country]">) {
  const { country } = await context.params;
  const iso2 = country.toUpperCase();
  if (!countries.some((item) => item.iso2 === iso2)) {
    return Response.json({ error: `Unknown country: ${iso2}.` }, { status: 404 });
  }
  const { rows } = await query<SeriesRow>(`
    with ranked_observations as (
      select i.slug, coalesce(ss.display_name, i.name) as name, coalesce(ss.unit, i.unit) as unit, coalesce(ss.frequency, i.frequency) as frequency, s.name as source_name,
        o.period_start::text, o.period_end::text, o.value::text, coalesce(o.as_of_date, o.period_start)::text as as_of_date, o.ingested_at::text,
        row_number() over (partition by i.slug order by o.period_start desc) as row_number
      from observations o join source_series ss on ss.id = o.source_series_id
      join indicators i on i.id = ss.indicator_id join sources s on s.id = ss.source_id join countries c on c.id = ss.country_id
      where c.iso2 = $1 and o.value is not null and o.period_start <= current_date
        -- CPI series for Russia and Ukraine are intentionally shown only from
        -- 2000 onwards: earlier observations are retained as raw provenance.
        and not (c.iso2 in ('RU', 'UA') and i.slug = 'inflation-cpi-annual' and o.period_start < date '2000-01-01')
    ) select slug, name, unit, frequency, source_name, period_start, period_end, value, as_of_date, ingested_at
    from ranked_observations where row_number <= 2_600 order by slug, period_start desc
  `, [iso2]);
  if (!rows.length) return Response.json({ error: `No data available for ${iso2}.` }, { status: 404 });

  const grouped = new Map<string, SeriesRow[]>();
  for (const row of rows) grouped.set(row.slug, [...(grouped.get(row.slug) ?? []), row]);
  const series = [...grouped.entries()].map(([slug, values]) => {
    const latest = toPoint(values[0]);
    const isInflationIndex = ["cpi", "core-cpi"].includes(slug) && values[0].unit === "index";
    const isInflationRate = ["cpi", "core-cpi", "inflation-cpi-annual"].includes(slug) && values[0].unit === "percent";
    const comparisonIndex = isInflationIndex ? values[0].frequency === "quarterly" ? 4 : 12 : 1;
    const comparison = values[comparisonIndex];
    const rawPoints = values.slice(0, historyLimits[slug] ?? 60).reverse().map(toPoint);
    const points = isInflationIndex
      ? rawPoints.map((point, index) => index < comparisonIndex ? null : { date: point.date, value: ((point.value / rawPoints[index - comparisonIndex].value) - 1) * 100 }).filter((point): point is MacroPoint => point !== null)
      : rawPoints;
    return { slug, name: values[0].name, unit: slug === "gdp-current-usd" ? "bn USD" : values[0].unit, sourceName: values[0].source_name, freshness: freshness(values[0]), latest, asOfDate: values[0].as_of_date, ingestedAt: values[0].ingested_at,
      change: isInflationRate ? latest.value : comparison ? isInflationIndex ? ((latest.value / Number(comparison.value)) - 1) * 100 : latest.value - Number(comparison.value) : undefined,
      points,
    } satisfies MacroSeries;
  });
  const { rows: eventRows } = await query<EventRow>(`
    select threads.id::text, threads.title, threads.event_type, threads.materiality,
      max(scores.total_score)::text as total_score,
      case max(case affected_countries.impact_scope when 'direct' then 3 when 'regional' then 2 else 1 end)
        when 3 then 'direct' when 2 then 'regional' else 'spillover' end as impact_scope,
      threads.last_occurred_at::text as occurred_at,
      string_agg(distinct sources.name, ' · ' order by sources.name) as source_name,
      (array_agg(raw.original_url order by sources.tier asc, articles.published_at desc))[1] as original_url,
      array_agg(distinct indicators.slug) filter (where indicators.slug is not null) as indicators,
      count(distinct sources.id)::int as source_count,
      case
        when count(reactions.event_id) > 0 then 'MARKET_CONFIRMED'
        when bool_or(sources.source_type = 'official') then 'OFFICIAL'
        when count(distinct sources.id) filter (where sources.slug <> 'gdelt-discovery') >= 2 then 'CORROBORATED'
        else 'UNVERIFIED'
      end as verification,
      case when bool_or(coalesce(scores.market_moving, false)) then 'MARKET_MOVING' else 'RESEARCH_SIGNAL' end as relevance
    from news_event_threads threads
    join news_event_thread_clusters thread_clusters on thread_clusters.thread_id = threads.id
    join news_event_clusters clusters on clusters.id = thread_clusters.cluster_id
    join news_event_countries affected_countries on affected_countries.event_id = clusters.id
    join countries event_country on event_country.id = affected_countries.country_id
    join news_event_articles event_articles on event_articles.event_id = clusters.id
    join news_articles articles on articles.id = event_articles.article_id
    join raw_documents raw on raw.id = articles.raw_document_id
    join sources on sources.id = raw.source_id
    left join news_event_scores scores on scores.event_id = clusters.id
    left join news_event_market_reactions reactions on reactions.event_id = clusters.id
    left join news_event_indicators affected_indicators on affected_indicators.event_id = clusters.id
    left join indicators on indicators.id = affected_indicators.indicator_id
    where event_country.iso2 = $1 and clusters.status = 'open'
      and threads.last_occurred_at >= now() - interval '45 days'
      and threads.last_occurred_at <= now()
    group by threads.id
    having bool_or(coalesce(scores.research_relevant, false))
    order by coalesce(max(scores.total_score), threads.materiality::numeric) desc, threads.last_occurred_at desc nulls last
    -- Filtering happens client-side so every impact and time filter must receive
    -- a sufficiently complete country event window rather than an arbitrary
    -- top-20 slice.
    limit 100
  `, [iso2]);
  const events = eventRows.map((event) => ({ id: event.id, title: event.title, eventType: event.event_type, materiality: event.materiality, score: event.total_score ? Number(event.total_score) : undefined, impactScope: event.impact_scope, occurredAt: event.occurred_at, sourceName: event.source_name, sourceCount: event.source_count, originalUrl: event.original_url, indicators: event.indicators ?? [], verification: event.verification, relevance: event.relevance })) satisfies MacroEvent[];
  const { rows: calendarRows } = await query<CalendarRow>(`
    select calendar.id::text, calendar.title, calendar.category, calendar.scheduled_at::text, calendar.timing_precision, calendar.importance, calendar.forecast_text, calendar.previous_text, calendar.currency_code, calendar.source_name, calendar.source_url
    from economic_calendar_events calendar
    join countries calendar_country on calendar_country.id = calendar.country_id
    where calendar_country.iso2 = $1 and calendar.status = 'scheduled'
      and calendar.scheduled_at >= now() and calendar.scheduled_at < now() + interval '31 days'
    order by calendar.scheduled_at asc, calendar.importance desc
    limit 250
  `, [iso2]);
  const calendar = calendarRows.map((event) => ({ id: event.id, title: event.title, category: event.category ?? undefined, scheduledAt: event.scheduled_at, timingPrecision: event.timing_precision, importance: event.importance, forecast: event.forecast_text ?? undefined, previous: event.previous_text ?? undefined, currency: event.currency_code ?? undefined, sourceName: event.source_name ?? undefined, sourceUrl: event.source_url ?? undefined })) satisfies CalendarEvent[];
  const { rows: calendarSourceRows } = await query<CalendarSourceRow>(`
    select distinct sources.name
    from economic_calendar_events calendar
    join countries calendar_country on calendar_country.id = calendar.country_id
    join sources on sources.id = calendar.source_id
    where calendar_country.iso2 = $1
      and calendar.status = 'scheduled'
      and calendar.scheduled_at >= now()
    order by sources.name
  `, [iso2]);
  const calendarSources = calendarSourceRows.map((source) => source.name);
  const { rows: healthRows } = await query<NewsHealthRow>(`
    select sources.slug, sources.name, latest.status, latest.completed_at::text, latest.records_written, latest.error_message
    from sources
    left join lateral (
      select status, completed_at, records_written, error_message
      from ingestion_runs where ingestion_runs.source_id = sources.id
      order by started_at desc limit 1
    ) latest on true
    where sources.active
      and (exists (select 1 from news_feeds where news_feeds.source_id = sources.id and news_feeds.active)
        or sources.slug in ('alpha-vantage-market-news', 'gdelt-discovery', 'federal-register-risk', 'businessquant-us-calendar', 'federal-reserve-fomc-calendar', 'bank-of-england'))
    order by sources.name
  `);
  const newsHealth = healthRows.map(toNewsHealth);
  return Response.json({ generatedAt: new Date().toISOString(), ...buildRegime(series), series, events, calendar, calendarSources, newsHealth } satisfies MacroDesk, { headers: { "Cache-Control": "no-store" } });
}
