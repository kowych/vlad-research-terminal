"use client";

import { useEffect, useMemo, useState } from "react";
import type { GlobalCalendarEvent, GlobalCalendarResponse } from "@/lib/macro";

type Horizon = "day" | "week" | "month";
type ImpactFilter = "all" | "market-moving";

const horizonDurations: Record<Horizon, number> = {
  day: 86_400_000,
  week: 7 * 86_400_000,
  month: 31 * 86_400_000,
};
const CALENDAR_VIEW_REFRESH_MS = 5 * 60_000;

const horizons: { value: Horizon; label: string }[] = [
  { value: "day", label: "DAY" },
  { value: "week", label: "WEEK" },
  { value: "month", label: "MONTH" },
];

function dayKey(scheduledAt: string) {
  return new Date(scheduledAt).toISOString().slice(0, 10);
}

function formatDay(day: string) {
  return new Date(`${day}T00:00:00Z`)
    .toLocaleDateString("en-GB", { weekday: "short", day: "2-digit", month: "short", timeZone: "UTC" })
    .toUpperCase();
}

function formatTiming(event: GlobalCalendarEvent) {
  if (event.timingPrecision === "date_only") return "TIME TBC";
  const time = new Date(event.scheduledAt).toLocaleTimeString("en-GB", {
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
    timeZone: "UTC",
  });
  return `${event.timingPrecision === "estimated" ? "EST. " : ""}${time} UTC`;
}

function impactLevel(importance: number) {
  return Math.min(3, Math.max(1, Math.ceil(importance / 2)));
}

function ImpactDots({ importance }: { importance: number }) {
  const level = impactLevel(importance);
  return <span className="calendar-impact" aria-label={`Impact ${level} of 3`}>
    {[1, 2, 3].map((dot) => <i key={dot} className={dot <= level ? "is-active" : ""} />)}
  </span>;
}

function CalendarEventRow({ event }: { event: GlobalCalendarEvent }) {
  const country = event.countryIso2 ?? "GLOBAL";
  const details = [country, event.currency, formatTiming(event), event.sourceName].filter(Boolean).join(" · ");
  const content = <>
    <ImpactDots importance={event.importance} />
    <div>
      <h3>{event.title}</h3>
      <p>{details}</p>
    </div>
    <span className="calendar-previous">{event.previous ? `PREV ${event.previous}` : "PREV —"}</span>
  </>;

  if (!event.sourceUrl) return <div className="calendar-event global-calendar-event">{content}</div>;

  return <a className="calendar-event global-calendar-event" href={event.sourceUrl} target="_blank" rel="noreferrer">
    {content}
  </a>;
}

export default function GlobalMacroCalendar() {
  const [calendar, setCalendar] = useState<GlobalCalendarResponse>();
  const [error, setError] = useState<string>();
  const [horizon, setHorizon] = useState<Horizon>("week");
  // Opening on the genuinely market-relevant release window keeps the first
  // read compact; lower-importance releases remain one click away under ALL.
  const [impact, setImpact] = useState<ImpactFilter>("market-moving");
  const [country, setCountry] = useState("all");

  useEffect(() => {
    let active = true;
    const refresh = async () => {
      try {
        const response = await fetch("/api/calendar");
        if (!response.ok) throw new Error("The calendar is temporarily unavailable.");
        const nextCalendar = await response.json() as GlobalCalendarResponse;
        if (active) {
          setCalendar(nextCalendar);
          setError(undefined);
        }
      } catch (reason) {
        if (active) setError(reason instanceof Error ? reason.message : "The calendar is temporarily unavailable.");
      }
    };

    void refresh();
    const interval = window.setInterval(() => void refresh(), CALENDAR_VIEW_REFRESH_MS);
    return () => {
      active = false;
      window.clearInterval(interval);
    };
  }, []);

  const countries = useMemo(() => {
    if (!calendar) return [];
    return [...new Map(calendar.events
      .filter((event): event is GlobalCalendarEvent & { countryIso2: string; countryName: string } => Boolean(event.countryIso2 && event.countryName))
      .map((event) => [event.countryIso2, event.countryName]))]
      .map(([iso2, name]) => ({ iso2, name }))
      .sort((left, right) => left.name.localeCompare(right.name));
  }, [calendar]);

  const visible = useMemo(() => {
    if (!calendar) return [];
    const reference = Date.parse(calendar.generatedAt);
    const deadline = reference + horizonDurations[horizon];
    return calendar.events
      .filter((event) => {
        const scheduledAt = Date.parse(event.scheduledAt);
        return Number.isFinite(scheduledAt)
          && scheduledAt >= reference
          && scheduledAt <= deadline
          && (country === "all" || event.countryIso2 === country)
          && (impact === "all" || event.importance >= 4);
      })
      .sort((left, right) => Date.parse(left.scheduledAt) - Date.parse(right.scheduledAt) || right.importance - left.importance || left.title.localeCompare(right.title));
  }, [calendar, country, horizon, impact]);

  const days = useMemo(() => {
    const grouped = new Map<string, GlobalCalendarEvent[]>();
    for (const event of visible) {
      const day = dayKey(event.scheduledAt);
      grouped.set(day, [...(grouped.get(day) ?? []), event]);
    }
    return [...grouped.entries()];
  }, [visible]);

  return <section className="global-calendar">
    <div className="section-label">
      <span>02 · GLOBAL VIEW</span>
      <h2>UPCOMING CALENDAR</h2>
      <span>{calendar ? `${visible.length} EVENT${visible.length === 1 ? "" : "S"} · ${horizon.toUpperCase()}` : "LOADING"}</span>
    </div>
    <p className="global-calendar-intro">Forward-looking official releases and policy decisions. Each item links to its primary source; exact times appear only when the source provides them.</p>
    {error && <p className="evidence-empty">{error.toUpperCase()}</p>}
    {!error && <>
      <div className="global-calendar-controls">
        <div className="evidence-filters" aria-label="Filter calendar period">
          {horizons.map((item) => <button type="button" key={item.value} className={horizon === item.value ? "is-active" : ""} onClick={() => setHorizon(item.value)}>{item.label}</button>)}
        </div>
        <div className="evidence-filters" aria-label="Filter calendar importance">
          <button type="button" className={impact === "all" ? "is-active" : ""} onClick={() => setImpact("all")}>ALL EVENTS</button>
          <button type="button" className={impact === "market-moving" ? "is-active" : ""} onClick={() => setImpact("market-moving")}>MARKET MOVING</button>
        </div>
        <label className="calendar-country-filter">
          <span>COUNTRY</span>
          <select value={country} onChange={(event) => setCountry(event.target.value)}>
            <option value="all">ALL MARKETS</option>
            {countries.map((item) => <option key={item.iso2} value={item.iso2}>{item.name}</option>)}
          </select>
        </label>
      </div>
      {!calendar && <p className="evidence-empty">LOADING UPCOMING RELEASES…</p>}
      {calendar && !visible.length && <p className="evidence-empty">NO EVENTS MATCH THIS FILTER FOR THE SELECTED PERIOD.</p>}
      {days.length > 0 && <div className="calendar-list global-calendar-list">
        {days.map(([day, events]) => <section className="calendar-day" key={day}>
          <header><span>{formatDay(day)}</span><span>{events.length} EVENT{events.length === 1 ? "" : "S"}</span></header>
          <div>{events.map((event) => <CalendarEventRow key={event.id} event={event} />)}</div>
        </section>)}
      </div>}
    </>}
  </section>;
}
