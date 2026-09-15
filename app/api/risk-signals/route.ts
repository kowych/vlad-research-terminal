import { query } from "@/lib/database";
import type { EventVerification, RiskEvent, RiskTapeResponse } from "@/lib/macro";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

type RiskEventRow = {
  id: string;
  title: string;
  event_type: string;
  materiality: number;
  total_score: string | null;
  impact_scope: "direct" | "regional" | "spillover";
  occurred_at: string;
  source_name: string;
  original_url: string;
  indicators: string[] | null;
  source_count: number;
  country_iso2: string[];
  verification: EventVerification;
};

export async function GET() {
  const { rows } = await query<RiskEventRow>(`
    select
      threads.id::text,
      threads.title,
      threads.event_type,
      threads.materiality,
      max(scores.total_score)::text as total_score,
      case max(case affected_countries.impact_scope when 'direct' then 3 when 'regional' then 2 else 1 end)
        when 3 then 'direct' when 2 then 'regional' else 'spillover' end as impact_scope,
      threads.last_occurred_at::text as occurred_at,
      string_agg(distinct sources.name, ' · ' order by sources.name) as source_name,
      (array_agg(raw.original_url order by sources.tier asc, articles.published_at desc))[1] as original_url,
      array_agg(distinct indicators.slug) filter (where indicators.slug is not null) as indicators,
      count(distinct sources.id)::int as source_count,
      array_agg(distinct event_country.iso2 order by event_country.iso2) as country_iso2,
      case
        when count(reactions.event_id) > 0 then 'MARKET_CONFIRMED'
        when bool_or(sources.source_type = 'official') then 'OFFICIAL'
        when count(distinct sources.id) filter (where sources.slug <> 'gdelt-discovery') >= 2 then 'CORROBORATED'
        else 'UNVERIFIED'
      end as verification
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
    where clusters.status = 'open'
    group by threads.id
    order by threads.last_occurred_at desc
    limit 250
  `);

  const events = rows.map((event) => ({
    id: event.id,
    title: event.title,
    eventType: event.event_type,
    materiality: event.materiality,
    score: event.total_score ? Number(event.total_score) : undefined,
    impactScope: event.impact_scope,
    occurredAt: event.occurred_at,
    sourceName: event.source_name,
    sourceCount: event.source_count,
    originalUrl: event.original_url,
    indicators: event.indicators ?? [],
    countryIso2: event.country_iso2,
    verification: event.verification,
  })) satisfies RiskEvent[];

  return Response.json({ generatedAt: new Date().toISOString(), events } satisfies RiskTapeResponse, {
    headers: { "Cache-Control": "no-store" },
  });
}
