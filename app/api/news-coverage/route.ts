import { newsCoverageDomains, type NewsCoverageDomain, type NewsCoverageResponse, type NewsCoverageSourceStatus } from "@/data/newsCoverage";
import { query } from "@/lib/database";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

type SourceRunRow = {
  slug: string;
  status: "completed" | "failed" | null;
  completed_at: string | null;
  records_written: number | null;
};

function sourceStatus(row?: SourceRunRow): NewsCoverageSourceStatus["status"] {
  if (!row?.status) return "PENDING";
  if (row.status === "failed") return "ATTENTION";
  const ageHours = row.completed_at ? (Date.now() - Date.parse(row.completed_at)) / 3_600_000 : Number.POSITIVE_INFINITY;
  return ageHours <= 36 ? "CURRENT" : "DELAYED";
}

function assessDomain(definition: typeof newsCoverageDomains[number], runsBySlug: Map<string, SourceRunRow>): NewsCoverageDomain {
  const sources = definition.sources.map((source) => {
    const run = runsBySlug.get(source.slug);
    return {
      ...source,
      status: sourceStatus(run),
      checkedAt: run?.completed_at ?? undefined,
      recordsWritten: run?.records_written ?? undefined,
    } satisfies NewsCoverageSourceStatus;
  });
  const currentPrimary = sources.filter((source) => source.role === "PRIMARY" && source.status === "CURRENT").length;
  const currentDiscovery = sources.filter((source) => source.role === "DISCOVERY" && source.status === "CURRENT").length;
  const primaryReady = currentPrimary >= definition.minimumCurrentPrimary;
  const discoveryReady = currentDiscovery >= (definition.minimumCurrentDiscovery ?? 0);
  const status = primaryReady && discoveryReady ? "LIVE" : primaryReady ? "PARTIAL" : "GAP";
  const currentLayers = [
    currentPrimary ? `${currentPrimary}/${definition.sources.filter((source) => source.role === "PRIMARY").length} primary current` : null,
    definition.sources.some((source) => source.role === "DISCOVERY") ? `${currentDiscovery}/${definition.sources.filter((source) => source.role === "DISCOVERY").length} discovery current` : null,
  ].filter(Boolean).join(" · ");
  const reason = status === "LIVE"
    ? `${currentLayers}. Required evidence layers are currently checked.`
    : `${currentLayers || "No current source checks"}. ${definition.missingLayer}`;
  return { slug: definition.slug, label: definition.label, description: definition.description, missingLayer: definition.missingLayer, status, reason, sources };
}

export async function GET() {
  const slugs = [...new Set(newsCoverageDomains.flatMap((domain) => domain.sources.map((source) => source.slug)))];
  const { rows } = await query<SourceRunRow>(`
    select sources.slug, latest.status, latest.completed_at::text, latest.records_written
    from sources
    left join lateral (
      select status, completed_at, records_written
      from ingestion_runs
      where ingestion_runs.source_id = sources.id
      order by started_at desc
      limit 1
    ) latest on true
    where sources.slug = any($1::text[])
  `, [slugs]);
  const runsBySlug = new Map(rows.map((row) => [row.slug, row]));
  const domains = newsCoverageDomains.map((domain) => assessDomain(domain, runsBySlug));
  return Response.json({ generatedAt: new Date().toISOString(), domains } satisfies NewsCoverageResponse, {
    headers: { "Cache-Control": "no-store" },
  });
}
