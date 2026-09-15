"use client";

import { useEffect, useMemo, useState } from "react";
import type { CalendarEvent, EventVerification, MacroDesk, MacroEvent, MacroPoint, MacroSeries, NewsSourceHealth } from "@/lib/macro";
import { topMetrics, type MetricDefinition } from "@/data/metrics";

function formatValue(value: number, unit: string) {
  if (unit === "percent") return `${value.toFixed(2)}%`;
  if (unit === "index") return value.toFixed(1);
  if (unit === "bn USD") return `$${value.toLocaleString(undefined, { maximumFractionDigits: 0 })}bn`;
  if (unit.includes("billions")) return `${value.toLocaleString(undefined, { maximumFractionDigits: 0 })} ${unit.replace("billions of ", "bn ")}`;
  return value.toLocaleString(undefined, { maximumFractionDigits: 0 });
}

function formatDate(value: string) { return new Date(`${value}T00:00:00Z`).toLocaleDateString("en-GB", { month: "short", year: "numeric", timeZone: "UTC" }).toUpperCase(); }

function Sparkline({ points }: { points: MacroPoint[] }) {
  if (points.length < 2) return null;
  const values = points.map((point) => point.value);
  const low = Math.min(...values);
  const high = Math.max(...values);
  const range = high - low || 1;
  const firstDate = Date.parse(`${points[0].date}T00:00:00Z`);
  const lastDate = Date.parse(`${points.at(-1)?.date}T00:00:00Z`);
  const dateRange = lastDate - firstDate || 1;
  const xFor = (value: string) => ((Date.parse(`${value}T00:00:00Z`) - firstDate) / dateRange) * 100;
  const path = points.map((point, index) => `${index === 0 ? "M" : "L"}${xFor(point.date)} ${30 - ((point.value - low) / range) * 26}`).join(" ");
  const startYear = new Date(firstDate).getUTCFullYear();
  const endYear = new Date(lastDate).getUTCFullYear();
  const firstTick = Math.ceil(startYear / 5) * 5;
  const ticks = Array.from({ length: Math.max(0, Math.floor(endYear / 5) - Math.ceil(startYear / 5) + 1) }, (_, index) => firstTick + index * 5);
  return <div className="macro-chart-wrap" role="img" aria-label={`Historical trend from ${startYear} to ${endYear}`}>
    <svg viewBox="0 0 100 36" preserveAspectRatio="none" className="macro-chart" aria-hidden="true">
      <path className="macro-chart-axis" d="M0 32H100" />
      <path className="macro-chart-line" d={path} />
      {ticks.map((year) => {
        const x = ((Date.UTC(year, 0, 1) - firstDate) / dateRange) * 100;
        return <path key={year} className="macro-chart-tick" d={`M${x} 32V35`} />;
      })}
    </svg>
    <div className="macro-axis-labels" aria-hidden="true">{ticks.map((year, index) => {
      const x = ((Date.UTC(year, 0, 1) - firstDate) / dateRange) * 100;
      const edgeClass = index === 0 ? "macro-axis-label is-first" : index === ticks.length - 1 ? "macro-axis-label is-last" : "macro-axis-label";
      return <span key={year} className={edgeClass} style={{ left: `${x}%` }}>{year}</span>;
    })}</div>
  </div>;
}

function SeriesCard({ definition, series }: { definition: MetricDefinition; series?: MacroSeries }) {
  if (!series) return <article className="live-series-card pending-series-card"><div className="series-heading"><p>{definition.label}</p><h2>—</h2></div><div className="series-pending"><p>CONNECTOR PENDING</p><span>{definition.connectorHint}</span></div></article>;
  const isInflation = ["cpi", "core-cpi", "inflation-cpi-annual"].includes(series.slug);
  return <article className="live-series-card">
    <div className="series-heading"><p>{definition.label}</p><h2>{isInflation && series.change !== undefined ? `${series.change.toFixed(2)}%` : formatValue(series.latest.value, series.unit)}</h2></div>
    <dl className="series-meta">
      <div><dt>PERIOD</dt><dd>{formatDate(series.latest.date)}</dd></div>
      <div><dt>OFFICIAL VINTAGE</dt><dd>{formatDate(series.asOfDate)}</dd></div>
      <div><dt>SOURCE</dt><dd>{series.sourceName}</dd></div>
      <div><dt>DATA STATUS</dt><dd>{series.freshness}</dd></div>
    </dl>
    <div className="series-chart"><Sparkline points={series.points} /></div>
  </article>;
}

const verificationLabels: Record<EventVerification, string> = {
  MARKET_CONFIRMED: "MARKET CONFIRMED",
  OFFICIAL: "OFFICIAL",
  CORROBORATED: "CORROBORATED",
  UNVERIFIED: "SIGNAL · UNVERIFIED",
};

function EvidenceTimeline({ events, referenceAt }: { events: MacroEvent[]; referenceAt: string }) {
  // Research desks should open on material events. The full evidence archive
  // remains one click away, but routine official communications no longer
  // dilute the initial macro read.
  const [filter, setFilter] = useState<"all" | "market" | "signals" | "direct" | "regional" | "spillover">("market");
  const [period, setPeriod] = useState<"day" | "week" | "month" | "all">("week");
  const referenceTime = Date.parse(referenceAt);
  const visible = events.filter((event) => {
    const age = referenceTime - Date.parse(event.occurredAt);
    const withinPeriod = period === "all" || (Number.isFinite(age) && age >= 0 && age <= { day: 86_400_000, week: 604_800_000, month: 2_592_000_000 }[period]);
    const matchesImpact = filter === "all"
      || (filter === "market" ? (event.score ?? event.materiality) >= 4 && event.verification !== "UNVERIFIED" : filter === "signals" ? event.verification === "UNVERIFIED" : event.impactScope === filter);
    return withinPeriod && matchesImpact;
  }).sort((a, b) => ((b.score ?? b.materiality) - (a.score ?? a.materiality)) || (Date.parse(b.occurredAt) - Date.parse(a.occurredAt)));
  const filters: { value: typeof filter; label: string }[] = [{ value: "all", label: "ALL" }, { value: "market", label: "MARKET MOVING" }, { value: "signals", label: "SIGNALS" }, { value: "direct", label: "DIRECT" }, { value: "regional", label: "REGIONAL" }, { value: "spillover", label: "SPILLOVER" }];
  const periods: { value: typeof period; label: string }[] = [{ value: "day", label: "DAY" }, { value: "week", label: "WEEK" }, { value: "month", label: "MONTH" }, { value: "all", label: "ALL TIME" }];
  return <section className="evidence-timeline"><div className="section-label"><span>EVIDENCE</span><h2>RECENT EVENTS</h2><span>{events.length ? `${events.length} EVENTS` : "NO LINKED EVENTS"}</span></div>{events.length ? <><div className="evidence-filter-groups"><div className="evidence-filters" aria-label="Filter event impact">{filters.map((item) => <button type="button" key={item.value} className={filter === item.value ? "is-active" : ""} onClick={() => setFilter(item.value)}>{item.label}</button>)}</div><div className="evidence-filters" aria-label="Filter event period">{periods.map((item) => <button type="button" key={item.value} className={period === item.value ? "is-active" : ""} onClick={() => setPeriod(item.value)}>{item.label}</button>)}</div></div><div className="evidence-list">{visible.map((event) => <a key={event.id} href={event.originalUrl} target="_blank" rel="noreferrer" className="evidence-item"><div><p>{new Date(event.occurredAt).toLocaleDateString("en-GB", { day: "2-digit", month: "short", year: "numeric", timeZone: "UTC" }).toUpperCase()} · {event.sourceName}{event.sourceCount > 1 ? ` · ${event.sourceCount} SOURCES` : ""}</p><h3>{event.title}</h3></div><div><span className={`risk-verification risk-${event.verification.toLowerCase().replaceAll("_", "-")}`}>{verificationLabels[event.verification]}</span><span>{event.impactScope} · S{(event.score ?? event.materiality).toFixed(1)}</span><span>{event.eventType.replaceAll("_", " ")}</span><span>{event.indicators.join(" · ") || "OFFICIAL COMMUNICATION"}</span></div></a>)}</div>{!visible.length && <p className="evidence-empty">NO EVENTS MATCH THIS FILTER FOR THE SELECTED PERIOD.</p>}</> : <p className="evidence-empty">OFFICIAL FEEDS ARE CONNECTED; THIS DESK HAS NO RULES-BASED EVENT LINKS YET.</p>}</section>;
}

const calendarHorizons = [
  { value: "day", label: "DAY", duration: 86_400_000 },
  { value: "week", label: "WEEK", duration: 7 * 86_400_000 },
  { value: "month", label: "MONTH", duration: 31 * 86_400_000 },
] as const;
const DESK_REFRESH_MS = 5 * 60_000;

function UpcomingCalendar({ events, referenceAt, sources }: { events: CalendarEvent[]; referenceAt: string; sources: string[] }) {
  const [horizon, setHorizon] = useState<(typeof calendarHorizons)[number]["value"]>("week");
  const hasConnector = sources.length > 0;
  const visible = useMemo(() => {
    const reference = Date.parse(referenceAt);
    const duration = calendarHorizons.find((item) => item.value === horizon)?.duration ?? 0;
    return events
      .filter((event) => {
        const scheduledAt = Date.parse(event.scheduledAt);
        return Number.isFinite(scheduledAt) && scheduledAt >= reference && scheduledAt <= reference + duration;
      })
      .sort((left, right) => Date.parse(left.scheduledAt) - Date.parse(right.scheduledAt) || right.importance - left.importance || left.title.localeCompare(right.title));
  }, [events, horizon, referenceAt]);
  const days = new Map<string, CalendarEvent[]>();
  for (const event of visible) {
    const day = new Date(event.scheduledAt).toISOString().slice(0, 10);
    days.set(day, [...(days.get(day) ?? []), event]);
  }
  const dayLabel = (day: string) => new Date(`${day}T00:00:00Z`).toLocaleDateString("en-GB", { weekday: "short", day: "2-digit", month: "short", timeZone: "UTC" }).toUpperCase();
  const impactLevel = (importance: number) => Math.min(3, Math.max(1, Math.ceil(importance / 2)));
  return <section className="calendar-strip"><div className="section-label"><span>FORWARD LOOKING</span><h2>UPCOMING CALENDAR</h2><span>{hasConnector ? `${visible.length} EVENT${visible.length === 1 ? "" : "S"} · ${horizon.toUpperCase()}` : "CONNECTOR PENDING"}</span></div>{hasConnector ? <><div className="evidence-filters" aria-label="Filter country calendar period">{calendarHorizons.map((item) => <button type="button" key={item.value} className={horizon === item.value ? "is-active" : ""} onClick={() => setHorizon(item.value)}>{item.label}</button>)}</div>{visible.length ? <div className="calendar-list">{[...days.entries()].sort(([left], [right]) => left.localeCompare(right)).map(([day, dayEvents]) => <section className="calendar-day" key={day}><header><span>{dayLabel(day)}</span><span>{dayEvents.length} RELEASE{dayEvents.length === 1 ? "" : "S"}</span></header><div>{dayEvents.map((event) => { const level = impactLevel(event.importance); const timing = event.timingPrecision === "date_only" ? "TIME TBC" : `${event.timingPrecision === "estimated" ? "EST. " : ""}${new Date(event.scheduledAt).toLocaleTimeString("en-GB", { hour: "2-digit", minute: "2-digit", timeZone: "UTC", hour12: false })} UTC`; return <a key={event.id} className="calendar-event" href={event.sourceUrl} target="_blank" rel="noreferrer"><span className="calendar-impact" aria-label={`Impact ${level} of 3`}>{[1, 2, 3].map((dot) => <i key={dot} className={dot <= level ? "is-active" : ""} />)}</span><div><h3>{event.title}</h3><p>{event.category?.toUpperCase() ?? "MACRO"} · {timing}</p></div><span className="calendar-previous">{event.previous ? `PREV ${event.previous}` : "PREV —"}</span></a>; })}</div></section>)}</div> : <p className="evidence-empty">NO SCHEDULED RELEASES IN THE SELECTED PERIOD.</p>}</> : <p className="evidence-empty">AN AUTHORISED CALENDAR PROVIDER IS REQUIRED BEFORE UPCOMING RELEASES CAN BE SHOWN.</p>}</section>;
}

function NewsPipelineHealth({ sources }: { sources: NewsSourceHealth[] }) {
  const current = sources.filter((source) => source.status === "CURRENT").length;
  return <section className="pipeline-health"><div className="section-label"><span>PIPELINE</span><h2>NEWS SOURCE HEALTH</h2><span>{current}/{sources.length} CURRENT</span></div><div className="pipeline-source-list">{sources.map((source) => <div key={source.slug} className={`pipeline-source pipeline-${source.status.toLowerCase()}`} title={source.error}><span>{source.name}</span><span>{source.status}{source.recordsWritten !== undefined ? ` · ${source.recordsWritten} NEW` : ""}</span></div>)}</div></section>;
}

export default function CountryMacroDesk({ country }: { country: string }) {
  const [desk, setDesk] = useState<MacroDesk>();
  const [error, setError] = useState<string>();
  useEffect(() => {
    let active = true;
    const refresh = async () => {
      try {
        const response = await fetch(`/api/macro/${country.toLowerCase()}`);
        if (!response.ok) throw new Error("Macro data is temporarily unavailable.");
        const nextDesk = await response.json() as MacroDesk;
        if (active) {
          setDesk(nextDesk);
          setError(undefined);
        }
      } catch (reason) {
        if (active) setError(reason instanceof Error ? reason.message : "Macro data is temporarily unavailable.");
      }
    };
    void refresh();
    const interval = window.setInterval(() => void refresh(), DESK_REFRESH_MS);
    return () => {
      active = false;
      window.clearInterval(interval);
    };
  }, [country]);
  if (error) return <p className="empty-line">{error.toUpperCase()}</p>;
  if (!desk) return <p className="empty-line">LOADING LIVE MACRO DATA…</p>;
  return <><section className="regime-card"><p>RULES-BASED REGIME</p><h2>{desk.regime}</h2><span>{desk.rationale}</span><small>REFRESHED {new Date(desk.generatedAt).toLocaleString("en-GB", { dateStyle: "medium", timeStyle: "short" })}</small></section><div className="live-series-grid">{topMetrics.map((definition) => <SeriesCard key={definition.key} definition={definition} series={desk.series.find((series) => definition.seriesSlugs.includes(series.slug))} />)}</div><UpcomingCalendar events={desk.calendar} referenceAt={desk.generatedAt} sources={desk.calendarSources} /><EvidenceTimeline events={desk.events} referenceAt={desk.generatedAt} /><NewsPipelineHealth sources={desk.newsHealth} /></>;
}
