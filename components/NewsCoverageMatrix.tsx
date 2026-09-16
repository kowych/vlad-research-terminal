"use client";

import { useEffect, useMemo, useState } from "react";
import type { NewsCoverageResponse, NewsCoverageState, NewsCoverageSourceStatus } from "@/data/newsCoverage";

const REFRESH_MS = 5 * 60_000;
const states: NewsCoverageState[] = ["LIVE", "PARTIAL", "GAP"];

function sourceDetail(source: NewsCoverageSourceStatus) {
  if (source.status !== "CURRENT") return source.status;
  if (source.recordsWritten === undefined) return "CURRENT";
  return `CURRENT · ${source.recordsWritten} NEW`;
}

export default function NewsCoverageMatrix() {
  const [coverage, setCoverage] = useState<NewsCoverageResponse>();
  const [error, setError] = useState<string>();
  const [filter, setFilter] = useState<"ALL" | NewsCoverageState>("ALL");

  useEffect(() => {
    let active = true;
    const refresh = async () => {
      try {
        const response = await fetch("/api/news-coverage");
        if (!response.ok) throw new Error("News coverage is temporarily unavailable.");
        const nextCoverage = await response.json() as NewsCoverageResponse;
        if (active) {
          setCoverage(nextCoverage);
          setError(undefined);
        }
      } catch (reason) {
        if (active) setError(reason instanceof Error ? reason.message : "News coverage is temporarily unavailable.");
      }
    };
    void refresh();
    const interval = window.setInterval(() => void refresh(), REFRESH_MS);
    return () => {
      active = false;
      window.clearInterval(interval);
    };
  }, []);

  const counts = useMemo(() => Object.fromEntries(states.map((state) => [state, coverage?.domains.filter((domain) => domain.status === state).length ?? 0])) as Record<NewsCoverageState, number>, [coverage]);
  const domains = useMemo(() => coverage?.domains.filter((domain) => filter === "ALL" || domain.status === filter) ?? [], [coverage?.domains, filter]);

  return <section className="news-coverage" aria-labelledby="news-coverage-heading">
    <div className="section-label"><span>04 · NEWS DATA QUALITY</span><h2 id="news-coverage-heading">NEWS COVERAGE MATRIX</h2><span>{coverage ? `${counts.LIVE}/${coverage.domains.length} LIVE` : "LOADING"}</span></div>
    <p className="news-coverage-intro">Coverage is measured from successful source checks, not from a source list. Discovery is never sufficient evidence for a published claim; it only accelerates the route to corroboration.</p>
    <div className="evidence-filters" aria-label="Filter news coverage status">
      <button type="button" className={filter === "ALL" ? "is-active" : ""} onClick={() => setFilter("ALL")}>ALL</button>
      {states.map((state) => <button type="button" className={filter === state ? "is-active" : ""} onClick={() => setFilter(state)} key={state}>{state} · {counts[state]}</button>)}
    </div>
    {error && <p className="evidence-empty">{error.toUpperCase()}</p>}
    {!coverage && !error && <p className="evidence-empty">ASSESSING NEWS EVIDENCE COVERAGE…</p>}
    {coverage && <div className="news-coverage-list">
      {domains.map((domain) => <details className="news-coverage-domain" key={domain.slug} open={domain.status !== "LIVE"}>
        <summary><span>{domain.label}</span><i className={`news-coverage-status news-coverage-${domain.status.toLowerCase()}`}>{domain.status}</i></summary>
        <div className="news-coverage-detail">
          <div><p className="news-coverage-description">{domain.description}</p><p className="news-coverage-reason">{domain.reason}</p></div>
          <div className="news-coverage-sources">{domain.sources.length ? domain.sources.map((source) => <div key={source.slug} className={`news-coverage-source source-${source.status.toLowerCase()}`}><span>{source.label} · {source.role}</span><span>{sourceDetail(source)}</span></div>) : <p className="news-coverage-reason">{domain.missingLayer}</p>}</div>
        </div>
      </details>)}
      {!domains.length && <p className="evidence-empty">NO COVERAGE DOMAIN MATCHES THIS FILTER.</p>}
    </div>}
  </section>;
}
