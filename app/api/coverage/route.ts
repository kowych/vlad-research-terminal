import { topMetrics, type MetricDefinition } from "@/data/metrics";
import { query } from "@/lib/database";
import type { CountryCoverage, CoverageDashboardResponse, CoverageState, MetricCoverage } from "@/lib/coverage";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

type Frequency = "daily" | "weekly" | "monthly" | "quarterly" | "annual" | "event";
type SourceType = "official" | "international" | "market" | "news" | "bootstrap";
type Candidate = {
  iso2: string;
  country_name: string;
  indicator_slug: string;
  source_name: string;
  source_type: SourceType;
  source_tier: number;
  frequency: Frequency;
  period_start: string;
  period_end: string | null;
  as_of_date: string;
};

const STATE_SCORE: Record<CoverageState, number> = { LIVE: 4, DELAYED: 3, PARTIAL: 2, MISSING: 1 };

function periodEnd(periodStart: string, frequency: Frequency): Date {
  const [year, month = 1, day = 1] = periodStart.split("-").map(Number);
  if (frequency === "monthly") return new Date(Date.UTC(year, month, 0));
  if (frequency === "quarterly") return new Date(Date.UTC(year, month + 2, 0));
  if (frequency === "annual") return new Date(Date.UTC(year, 11, 31));
  if (frequency === "weekly") return new Date(Date.UTC(year, month - 1, day + 6));
  return new Date(Date.UTC(year, month - 1, day));
}

function ageInDays(definition: MetricDefinition, candidate: Candidate): number {
  // A policy rate can remain unchanged for months. For this metric freshness
  // means that its official source was checked recently, not that a rate move
  // occurred recently.
  const periodReference = definition.key === "policy"
    ? new Date(`${candidate.as_of_date}T00:00:00Z`)
    : candidate.period_end ? new Date(`${candidate.period_end}T00:00:00Z`) : periodEnd(candidate.period_start, candidate.frequency);
  return Math.max(0, Math.floor((Date.now() - periodReference.getTime()) / 86_400_000));
}

function assess(definition: MetricDefinition, candidate?: Candidate): MetricCoverage {
  if (!candidate) {
    return { key: definition.key, label: definition.label, status: "MISSING", reason: "No source-series connector has produced an observation for this metric." };
  }

  const sourceDetails = { sourceName: candidate.source_name, sourceType: candidate.source_type, frequency: candidate.frequency, periodStart: candidate.period_start, asOfDate: candidate.as_of_date } as const;
  if (!definition.acceptedSourceTypes.includes(candidate.source_type as "official" | "international" | "market")) {
    return { key: definition.key, label: definition.label, status: "PARTIAL", reason: `${candidate.source_name} is not an approved source type for live coverage.`, ...sourceDetails };
  }
  if (!definition.acceptedFrequencies.includes(candidate.frequency as "daily" | "weekly" | "monthly" | "quarterly")) {
    return { key: definition.key, label: definition.label, status: "PARTIAL", reason: `${candidate.frequency.toUpperCase()} coverage is a structural baseline; ${definition.connectorHint.toLowerCase()} is required.`, ...sourceDetails };
  }

  const age = ageInDays(definition, candidate);
  if (age > definition.maximumAgeDays) {
    const reference = definition.key === "policy" ? "Official source check" : "Latest reference period";
    return { key: definition.key, label: definition.label, status: "DELAYED", reason: `${reference} is ${age} days old; the live threshold is ${definition.maximumAgeDays} days.`, ...sourceDetails };
  }
  const reference = definition.key === "policy" ? "official source check" : "latest period";
  return { key: definition.key, label: definition.label, status: "LIVE", reason: `Approved ${candidate.source_type} source at ${candidate.frequency} cadence; ${reference} is ${age} days old.`, ...sourceDetails };
}

function chooseBest(definition: MetricDefinition, candidates: Candidate[]): MetricCoverage {
  const evaluated = candidates.map((candidate) => ({ candidate, coverage: assess(definition, candidate) }));
  evaluated.sort((left, right) => {
    const stateDifference = STATE_SCORE[right.coverage.status] - STATE_SCORE[left.coverage.status];
    if (stateDifference) return stateDifference;
    const tierDifference = left.candidate.source_tier - right.candidate.source_tier;
    if (tierDifference) return tierDifference;
    return right.candidate.period_start.localeCompare(left.candidate.period_start);
  });
  return evaluated[0]?.coverage ?? assess(definition);
}

function countryState(metrics: MetricCoverage[]): CoverageState {
  if (metrics.every((metric) => metric.status === "LIVE")) return "LIVE";
  if (metrics.some((metric) => metric.status === "DELAYED")) return "DELAYED";
  if (metrics.every((metric) => metric.status === "MISSING")) return "MISSING";
  return "PARTIAL";
}

export async function GET() {
  const seriesSlugs = [...new Set(topMetrics.flatMap((metric) => metric.seriesSlugs))];
  const { rows } = await query<Candidate>(`
    select distinct on (countries.iso2, indicators.slug, source_series.id)
      countries.iso2,
      countries.name as country_name,
      indicators.slug as indicator_slug,
      sources.name as source_name,
      sources.source_type,
      sources.tier as source_tier,
      coalesce(source_series.frequency, indicators.frequency) as frequency,
      observations.period_start::text,
      observations.period_end::text,
      coalesce(observations.as_of_date, observations.period_start)::text as as_of_date
    from observations
    join source_series on source_series.id = observations.source_series_id
    join indicators on indicators.id = source_series.indicator_id
    join sources on sources.id = source_series.source_id
    join countries on countries.id = source_series.country_id
    where countries.active
      and observations.value is not null
      and observations.period_start <= current_date
      and indicators.slug = any($1::text[])
    order by countries.iso2, indicators.slug, source_series.id,
      observations.period_start desc,
      coalesce(observations.as_of_date, observations.period_start) desc,
      observations.ingested_at desc
  `, [seriesSlugs]);

  const candidatesByCountryAndSlug = new Map<string, Candidate[]>();
  for (const row of rows) {
    const key = `${row.iso2}:${row.indicator_slug}`;
    candidatesByCountryAndSlug.set(key, [...(candidatesByCountryAndSlug.get(key) ?? []), row]);
  }
  const countryNames = new Map<string, string>();
  for (const row of rows) countryNames.set(row.iso2, row.country_name);
  const { rows: countriesWithoutSeries } = await query<{ iso2: string; name: string }>("select iso2, name from countries where active order by name");
  for (const country of countriesWithoutSeries) countryNames.set(country.iso2, country.name);

  const countries = [...countryNames.entries()]
    .map(([iso2, name]) => {
      const metrics = topMetrics.map((definition) => {
        const candidates = definition.seriesSlugs.flatMap((slug) => candidatesByCountryAndSlug.get(`${iso2}:${slug}`) ?? []);
        return chooseBest(definition, candidates);
      });
      return { iso2, name, status: countryState(metrics), liveMetricCount: metrics.filter((metric) => metric.status === "LIVE").length, metrics } satisfies CountryCoverage;
    })
    .sort((left, right) => right.liveMetricCount - left.liveMetricCount || left.name.localeCompare(right.name));

  return Response.json({ generatedAt: new Date().toISOString(), countries } satisfies CoverageDashboardResponse, { headers: { "Cache-Control": "no-store" } });
}
