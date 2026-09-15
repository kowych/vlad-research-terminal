"use client";

import { useEffect, useMemo, useState } from "react";
import type { CoverageDashboardResponse, CoverageState, MetricCoverage } from "@/lib/coverage";

const states: CoverageState[] = ["LIVE", "PARTIAL", "DELAYED", "MISSING"];

function formatDate(value?: string) {
  if (!value) return "—";
  return new Date(`${value}T00:00:00Z`).toLocaleDateString("en-GB", { month: "short", year: "numeric", timeZone: "UTC" }).toUpperCase();
}

function CoverageMetric({ metric }: { metric: MetricCoverage }) {
  return <article className="coverage-metric">
    <div className="coverage-metric-heading"><p>{metric.label}</p><span className={`coverage-status coverage-${metric.status.toLowerCase()}`}>{metric.status}</span></div>
    <p className="coverage-reason">{metric.reason}</p>
    {metric.sourceName && <p className="coverage-provenance">{metric.sourceName} · {metric.frequency?.toUpperCase()} · PERIOD {formatDate(metric.periodStart)} · VINTAGE {formatDate(metric.asOfDate)}</p>}
  </article>;
}

export default function CoverageDashboard() {
  const [dashboard, setDashboard] = useState<CoverageDashboardResponse>();
  const [error, setError] = useState<string>();
  const [stateFilter, setStateFilter] = useState<"ALL" | CoverageState>("ALL");
  const [countryFilter, setCountryFilter] = useState("ALL");

  useEffect(() => {
    const controller = new AbortController();
    fetch("/api/coverage", { signal: controller.signal })
      .then(async (response) => {
        if (!response.ok) throw new Error("Coverage data is temporarily unavailable.");
        return response.json() as Promise<CoverageDashboardResponse>;
      })
      .then(setDashboard)
      .catch((reason: unknown) => {
        if (reason instanceof DOMException && reason.name === "AbortError") return;
        setError(reason instanceof Error ? reason.message : "Coverage data is temporarily unavailable.");
      });
    return () => controller.abort();
  }, []);

  const visibleCountries = useMemo(() => dashboard?.countries.filter((country) =>
    (countryFilter === "ALL" || country.iso2 === countryFilter)
      && (stateFilter === "ALL" || country.metrics.some((metric) => metric.status === stateFilter)),
  ) ?? [], [countryFilter, dashboard?.countries, stateFilter]);
  const counts = useMemo(() => Object.fromEntries(states.map((state) => [state, dashboard?.countries.flatMap((country) => country.metrics).filter((metric) => metric.status === state).length ?? 0])) as Record<CoverageState, number>, [dashboard?.countries]);

  return <section className="coverage-dashboard" aria-labelledby="coverage-heading">
    <div className="section-label"><span>03 · DATA QUALITY</span><h2 id="coverage-heading">SIX-METRIC COVERAGE</h2><span>{dashboard ? `${counts.LIVE}/${dashboard.countries.length * 6} LIVE` : "LOADING"}</span></div>
    <p className="coverage-intro">LIVE means an approved source, a suitable reporting cadence and a current reference period. The dashboard exposes every lower-quality fallback instead of presenting it as current data.</p>
    {error && <p className="evidence-empty">{error.toUpperCase()}</p>}
    {!dashboard && !error && <p className="evidence-empty">ASSESSING SOURCE COVERAGE…</p>}
    {dashboard && <>
      <div className="coverage-controls">
        <div className="evidence-filters" aria-label="Filter coverage status">
          <button type="button" className={stateFilter === "ALL" ? "is-active" : ""} onClick={() => setStateFilter("ALL")}>ALL</button>
          {states.map((state) => <button type="button" className={stateFilter === state ? "is-active" : ""} onClick={() => setStateFilter(state)} key={state}>{state} · {counts[state]}</button>)}
        </div>
        <label className="calendar-country-filter">COUNTRY
          <select value={countryFilter} onChange={(event) => setCountryFilter(event.target.value)}>
            <option value="ALL">ALL COUNTRIES</option>
            {dashboard.countries.map((country) => <option value={country.iso2} key={country.iso2}>{country.name.toUpperCase()}</option>)}
          </select>
        </label>
      </div>
      <div className="coverage-country-list">
        {visibleCountries.map((country) => {
          const metrics = stateFilter === "ALL" ? country.metrics : country.metrics.filter((metric) => metric.status === stateFilter);
          return <details className="coverage-country" key={country.iso2} open={country.status === "LIVE" || country.iso2 === countryFilter}>
            <summary><span>{country.name.toUpperCase()}</span><span>{country.liveMetricCount}/6 LIVE · <i className={`coverage-status coverage-${country.status.toLowerCase()}`}>{country.status}</i></span></summary>
            <div className="coverage-metric-list">{metrics.map((metric) => <CoverageMetric metric={metric} key={metric.key} />)}</div>
          </details>;
        })}
      </div>
      {!visibleCountries.length && <p className="evidence-empty">NO COUNTRY MATCHES THIS FILTER.</p>}
    </>}
  </section>;
}
