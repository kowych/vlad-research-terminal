import { query } from "@/lib/database";
import type { CalendarEvent, MacroEvent, MacroPoint, MacroSeries, UsMacroDesk } from "@/lib/macro";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

type SeriesRow = { slug: string; name: string; unit: string; frequency: "daily" | "weekly" | "monthly" | "quarterly" | "annual" | "event"; source_name: string; period_start: string; value: string; as_of_date: string; ingested_at: string };
type EventRow = { id: string; title: string; event_type: string; materiality: number; total_score: string | null; impact_scope: "direct" | "regional" | "spillover"; occurred_at: string; source_name: string; original_url: string; indicators: string[] | null };
type CalendarRow = { id: string; title: string; category: string | null; scheduled_at: string; importance: number; forecast_text: string | null; previous_text: string | null; currency_code: string | null; source_name: string | null; source_url: string | null };

const historyLimits: Record<string, number> = {
  "policy-rate": 2_600, cpi: 180, "unemployment-rate": 180, "nonfarm-payrolls": 180,
  "real-gdp": 80, "treasury-2y": 2_600, "treasury-10y": 2_600,
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
  const ageInDays = (Date.now() - Date.parse(`${row.period_start}T00:00:00Z`)) / 86_400_000;
  const maximumAge = { daily: 10, weekly: 21, monthly: 62, quarterly: 160, event: 7 }[row.frequency];
  return ageInDays <= maximumAge ? "CURRENT" : "DELAYED";
}

function buildRegime(series: MacroSeries[]): Pick<UsMacroDesk, "regime" | "rationale"> {
  const bySlug = new Map(series.map((item) => [item.slug, item]));
  const inflation = bySlug.get("cpi")?.change ?? bySlug.get("inflation-cpi-annual")?.latest.value;
  const unemployment = bySlug.get("unemployment-rate")?.latest.value ?? bySlug.get("unemployment-total")?.latest.value;
  const policyRate = bySlug.get("policy-rate")?.latest.value;
  if (inflation !== undefined && policyRate !== undefined && inflation > policyRate) return { regime: "INFLATION PRESSURE", rationale: "Available annual inflation is above the available policy-rate measure." };
  if (unemployment !== undefined && unemployment > 5) return { regime: "LABOUR-MARKET STRESS", rationale: "The unemployment rate is above the current 5% monitoring threshold." };
  return { regime: "MONITORING", rationale: "A rules-based provisional label; it will be expanded with documented scenario logic." };
}

export async function GET(_request: Request, context: RouteContext<"/api/macro/[country]">) {
  const { country } = await context.params;
  const iso2 = country.toUpperCase();
  const { rows } = await query<SeriesRow>(`
    with ranked_observations as (
      select i.slug, coalesce(ss.display_name, i.name) as name, coalesce(ss.unit, i.unit) as unit, i.frequency, s.name as source_name,
        o.period_start::text, o.value::text, o.as_of_date::text, o.ingested_at::text,
        row_number() over (partition by i.slug order by o.period_start desc) as row_number
      from observations o join source_series ss on ss.id = o.source_series_id
      join indicators i on i.id = ss.indicator_id join sources s on s.id = ss.source_id join countries c on c.id = ss.country_id
      where c.iso2 = $1 and o.value is not null and o.period_start <= current_date
        -- CPI series for Russia and Ukraine are intentionally shown only from
        -- 2000 onwards: earlier observations are retained as raw provenance.
        and not (c.iso2 in ('RU', 'UA') and i.slug = 'inflation-cpi-annual' and o.period_start < date '2000-01-01')
    ) select slug, name, unit, frequency, source_name, period_start, value, as_of_date, ingested_at
    from ranked_observations where row_number <= 2_600 order by slug, period_start desc
  `, [iso2]);
  if (!rows.length) return Response.json({ error: `No data available for ${iso2}.` }, { status: 404 });

  const grouped = new Map<string, SeriesRow[]>();
  for (const row of rows) grouped.set(row.slug, [...(grouped.get(row.slug) ?? []), row]);
  const series = [...grouped.entries()].map(([slug, values]) => {
    const latest = toPoint(values[0]); const comparisonIndex = slug === "cpi" ? 12 : 1; const comparison = values[comparisonIndex];
    const rawPoints = values.slice(0, historyLimits[slug] ?? 60).reverse().map(toPoint);
    const points = slug === "cpi"
      ? rawPoints.map((point, index) => index < 12 ? null : { date: point.date, value: ((point.value / rawPoints[index - 12].value) - 1) * 100 }).filter((point): point is MacroPoint => point !== null)
      : rawPoints;
    return { slug, name: values[0].name, unit: slug === "gdp-current-usd" ? "bn USD" : values[0].unit, sourceName: values[0].source_name, freshness: freshness(values[0]), latest, asOfDate: values[0].as_of_date, ingestedAt: values[0].ingested_at,
      change: comparison ? slug === "cpi" ? ((latest.value / Number(comparison.value)) - 1) * 100 : latest.value - Number(comparison.value) : undefined,
      points,
    } satisfies MacroSeries;
  });
  const { rows: eventRows } = await query<EventRow>(`
    select clusters.id::text, clusters.title, clusters.event_type, clusters.materiality, scores.total_score::text, affected_countries.impact_scope, clusters.occurred_at::text,
      sources.name as source_name, raw.original_url, array_agg(distinct indicators.slug) filter (where indicators.slug is not null) as indicators
    from news_event_clusters clusters
    join news_event_countries affected_countries on affected_countries.event_id = clusters.id
    join countries event_country on event_country.id = affected_countries.country_id
    join news_event_articles event_articles on event_articles.event_id = clusters.id
    join news_articles articles on articles.id = event_articles.article_id
    join raw_documents raw on raw.id = articles.raw_document_id
    join sources on sources.id = raw.source_id
    left join news_event_scores scores on scores.event_id = clusters.id
    left join news_event_indicators affected_indicators on affected_indicators.event_id = clusters.id
    left join indicators on indicators.id = affected_indicators.indicator_id
    where event_country.iso2 = $1 and clusters.status = 'open'
    group by clusters.id, scores.total_score, affected_countries.impact_scope, sources.name, raw.original_url
    order by coalesce(scores.total_score, clusters.materiality::numeric) desc, clusters.occurred_at desc nulls last
    limit 20
  `, [iso2]);
  const events = eventRows.map((event) => ({ id: event.id, title: event.title, eventType: event.event_type, materiality: event.materiality, score: event.total_score ? Number(event.total_score) : undefined, impactScope: event.impact_scope, occurredAt: event.occurred_at, sourceName: event.source_name, originalUrl: event.original_url, indicators: event.indicators ?? [] })) satisfies MacroEvent[];
  const { rows: calendarRows } = await query<CalendarRow>(`
    select calendar.id::text, calendar.title, calendar.category, calendar.scheduled_at::text, calendar.importance, calendar.forecast_text, calendar.previous_text, calendar.currency_code, calendar.source_name, calendar.source_url
    from economic_calendar_events calendar
    join countries calendar_country on calendar_country.id = calendar.country_id
    where calendar_country.iso2 = $1 and calendar.status = 'scheduled'
      and calendar.scheduled_at >= now() and calendar.scheduled_at < now() + interval '14 days'
    order by calendar.importance desc, calendar.scheduled_at asc
    limit 10
  `, [iso2]);
  const calendar = calendarRows.map((event) => ({ id: event.id, title: event.title, category: event.category ?? undefined, scheduledAt: event.scheduled_at, importance: event.importance, forecast: event.forecast_text ?? undefined, previous: event.previous_text ?? undefined, currency: event.currency_code ?? undefined, sourceName: event.source_name ?? undefined, sourceUrl: event.source_url ?? undefined })) satisfies CalendarEvent[];
  return Response.json({ generatedAt: new Date().toISOString(), ...buildRegime(series), series, events, calendar } satisfies UsMacroDesk, { headers: { "Cache-Control": "no-store" } });
}
