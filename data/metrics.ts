export type MetricDefinition = {
  key: "policy" | "headline-inflation" | "core-inflation" | "unemployment" | "real-gdp-growth" | "sovereign-10y";
  label: string;
  seriesSlugs: string[];
  connectorHint: string;
  // A source can only be labelled LIVE when it meets every one of these
  // explicit rules. They live beside the research metric definitions, rather
  // than being duplicated in a UI component or a database query.
  acceptedFrequencies: Array<"daily" | "weekly" | "monthly" | "quarterly">;
  maximumAgeDays: number;
  acceptedSourceTypes: Array<"official" | "international" | "market">;
};

// The only six metrics shown on every country desk. A fallback is permitted
// only when it measures the same concept at a lower frequency; unrelated US
// series never displace a missing slot on another country's desk.
export const topMetrics: MetricDefinition[] = [
  { key: "policy", label: "POLICY RATE", seriesSlugs: ["policy-rate"], connectorHint: "Official central-bank rate", acceptedFrequencies: ["daily", "weekly", "monthly"], maximumAgeDays: 35, acceptedSourceTypes: ["official", "international"] },
  { key: "headline-inflation", label: "HEADLINE INFLATION · YOY", seriesSlugs: ["cpi", "inflation-cpi-annual"], connectorHint: "Official CPI or HICP release", acceptedFrequencies: ["monthly", "quarterly"], maximumAgeDays: 130, acceptedSourceTypes: ["official", "international"] },
  { key: "core-inflation", label: "CORE INFLATION · YOY", seriesSlugs: ["core-cpi"], connectorHint: "Official core CPI or HICP release", acceptedFrequencies: ["monthly", "quarterly"], maximumAgeDays: 130, acceptedSourceTypes: ["official", "international"] },
  { key: "unemployment", label: "UNEMPLOYMENT RATE", seriesSlugs: ["unemployment-rate", "unemployment-total"], connectorHint: "Official labour-market release", acceptedFrequencies: ["monthly", "quarterly"], maximumAgeDays: 130, acceptedSourceTypes: ["official", "international"] },
  { key: "real-gdp-growth", label: "REAL GDP GROWTH", seriesSlugs: ["real-gdp-growth", "gdp-growth-annual"], connectorHint: "Official quarterly GDP release", acceptedFrequencies: ["quarterly"], maximumAgeDays: 200, acceptedSourceTypes: ["official", "international"] },
  { key: "sovereign-10y", label: "10Y SOVEREIGN YIELD", seriesSlugs: ["treasury-10y", "sovereign-10y"], connectorHint: "Official or licensed sovereign-yield source", acceptedFrequencies: ["daily", "weekly", "monthly"], maximumAgeDays: 50, acceptedSourceTypes: ["official", "international", "market"] },
];
