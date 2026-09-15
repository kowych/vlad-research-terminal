"use client";

import { useEffect, useMemo, useState } from "react";
import { countries } from "@/data/countries";
import type { EventVerification, RiskEvent, RiskTapeResponse } from "@/lib/macro";

const REFRESH_MS = 5 * 60_000;
const verificationOrder: Record<EventVerification, number> = {
  MARKET_CONFIRMED: 4,
  OFFICIAL: 3,
  CORROBORATED: 2,
  UNVERIFIED: 1,
};
const verificationLabels: Record<EventVerification, string> = {
  MARKET_CONFIRMED: "MARKET CONFIRMED",
  OFFICIAL: "OFFICIAL",
  CORROBORATED: "CORROBORATED",
  UNVERIFIED: "SIGNAL · UNVERIFIED",
};
const periods = [
  { value: "day", label: "DAY", duration: 86_400_000 },
  { value: "week", label: "WEEK", duration: 7 * 86_400_000 },
  { value: "month", label: "MONTH", duration: 31 * 86_400_000 },
] as const;

function formatCountries(event: RiskEvent) {
  const names = event.countryIso2
    .map((iso2) => countries.find((country) => country.iso2 === iso2)?.name ?? iso2)
    .slice(0, 4);
  return event.countryIso2.length > names.length ? `${names.join(" · ")} +${event.countryIso2.length - names.length}` : names.join(" · ");
}

export default function GlobalRiskTape() {
  const [tape, setTape] = useState<RiskTapeResponse>();
  const [error, setError] = useState<string>();
  const [verification, setVerification] = useState<"all" | EventVerification>("all");
  const [period, setPeriod] = useState<(typeof periods)[number]["value"]>("week");

  useEffect(() => {
    let active = true;
    const refresh = async () => {
      try {
        const response = await fetch("/api/risk-signals");
        if (!response.ok) throw new Error("Risk signals are temporarily unavailable.");
        const nextTape = await response.json() as RiskTapeResponse;
        if (active) {
          setTape(nextTape);
          setError(undefined);
        }
      } catch (reason) {
        if (active) setError(reason instanceof Error ? reason.message : "Risk signals are temporarily unavailable.");
      }
    };
    void refresh();
    const interval = window.setInterval(() => void refresh(), REFRESH_MS);
    return () => {
      active = false;
      window.clearInterval(interval);
    };
  }, []);

  const visible = useMemo(() => {
    if (!tape) return [];
    const reference = Date.parse(tape.generatedAt);
    const duration = periods.find((item) => item.value === period)?.duration ?? 0;
    return tape.events
      .filter((event) => {
        const occurredAt = Date.parse(event.occurredAt);
        return Number.isFinite(occurredAt)
          && occurredAt <= reference
          && occurredAt >= reference - duration
          && (verification === "all" || event.verification === verification);
      })
      .sort((left, right) => {
        const verificationDifference = verificationOrder[right.verification] - verificationOrder[left.verification];
        if (verificationDifference) return verificationDifference;
        const scoreDifference = (right.score ?? right.materiality) - (left.score ?? left.materiality);
        return scoreDifference || Date.parse(right.occurredAt) - Date.parse(left.occurredAt);
      });
  }, [period, tape, verification]);

  const filters: { value: "all" | EventVerification; label: string }[] = [
    { value: "all", label: "ALL" },
    { value: "UNVERIFIED", label: "SIGNALS" },
    { value: "CORROBORATED", label: "CORROBORATED" },
    { value: "OFFICIAL", label: "OFFICIAL" },
    { value: "MARKET_CONFIRMED", label: "MARKET CONFIRMED" },
  ];

  return <section className="risk-tape">
    <div className="section-label">
      <span>GEOPOLITICAL & POLICY RISK</span>
      <h2>GLOBAL RISK TAPE</h2>
      <span>{tape ? `${visible.length} EVENT${visible.length === 1 ? "" : "S"} · ${period.toUpperCase()}` : "LOADING"}</span>
    </div>
    <p className="risk-tape-intro">Unverified signals remain visible for early research. They are not evidence of a market move and cannot enter an AI conclusion without corroboration.</p>
    <div className="risk-tape-controls">
      <div className="evidence-filters" aria-label="Filter risk signal verification">
        {filters.map((item) => <button type="button" key={item.value} className={verification === item.value ? "is-active" : ""} onClick={() => setVerification(item.value)}>{item.label}</button>)}
      </div>
      <div className="evidence-filters" aria-label="Filter risk signal period">
        {periods.map((item) => <button type="button" key={item.value} className={period === item.value ? "is-active" : ""} onClick={() => setPeriod(item.value)}>{item.label}</button>)}
      </div>
    </div>
    {error && <p className="evidence-empty">{error.toUpperCase()}</p>}
    {!error && tape && <div className="evidence-list">
      {visible.map((event) => <a key={event.id} href={event.originalUrl} target="_blank" rel="noreferrer" className="evidence-item risk-event">
        <div>
          <p>{new Date(event.occurredAt).toLocaleDateString("en-GB", { day: "2-digit", month: "short", year: "numeric", timeZone: "UTC" }).toUpperCase()} · {event.sourceName}{event.sourceCount > 1 ? ` · ${event.sourceCount} SOURCES` : ""}</p>
          <h3>{event.title}</h3>
        </div>
        <div>
          <span className={`risk-verification risk-${event.verification.toLowerCase().replaceAll("_", "-")}`}>{verificationLabels[event.verification]}</span>
          <span>{formatCountries(event) || "GLOBAL"}</span>
          <span>{event.impactScope} · S{(event.score ?? event.materiality).toFixed(1)}</span>
        </div>
      </a>)}
      {!visible.length && <p className="evidence-empty">NO RISK EVENTS MATCH THIS FILTER FOR THE SELECTED PERIOD.</p>}
    </div>}
  </section>;
}
