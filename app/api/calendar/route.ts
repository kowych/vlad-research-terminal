import { query } from "@/lib/database";
import type { GlobalCalendarEvent, GlobalCalendarResponse } from "@/lib/macro";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

type CalendarRow = {
  id: string;
  title: string;
  category: string | null;
  scheduled_at: string;
  timing_precision: "exact" | "estimated" | "date_only";
  importance: number;
  forecast_text: string | null;
  previous_text: string | null;
  currency_code: string | null;
  source_name: string | null;
  source_url: string | null;
  country_iso2: string | null;
  country_name: string | null;
};

export async function GET() {
  const { rows } = await query<CalendarRow>(`
    select
      calendar.id::text,
      calendar.title,
      calendar.category,
      calendar.scheduled_at::text,
      calendar.timing_precision,
      calendar.importance,
      calendar.forecast_text,
      calendar.previous_text,
      calendar.currency_code,
      coalesce(calendar.source_name, source.name) as source_name,
      coalesce(calendar.source_url, calendar.original_url, source.base_url) as source_url,
      country.iso2 as country_iso2,
      country.name as country_name
    from economic_calendar_events calendar
    join sources source on source.id = calendar.source_id
    left join countries country on country.id = calendar.country_id
    where source.active
      and calendar.status = 'scheduled'
      and calendar.scheduled_at >= now()
      and calendar.scheduled_at < now() + interval '90 days'
    order by calendar.scheduled_at asc, calendar.importance desc, calendar.title asc
    limit 250
  `);

  const events = rows.map((event) => ({
    id: event.id,
    title: event.title,
    category: event.category ?? undefined,
    scheduledAt: event.scheduled_at,
    timingPrecision: event.timing_precision,
    importance: event.importance,
    forecast: event.forecast_text ?? undefined,
    previous: event.previous_text ?? undefined,
    currency: event.currency_code ?? undefined,
    sourceName: event.source_name ?? undefined,
    sourceUrl: event.source_url ?? undefined,
    countryIso2: event.country_iso2 ?? undefined,
    countryName: event.country_name ?? undefined,
  })) satisfies GlobalCalendarEvent[];

  return Response.json(
    { generatedAt: new Date().toISOString(), events } satisfies GlobalCalendarResponse,
    { headers: { "Cache-Control": "no-store" } },
  );
}
