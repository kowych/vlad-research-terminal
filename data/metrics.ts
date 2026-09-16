export type MetricDefinition = {
  key: "core-inflation" | "gdp" | "unemployment" | "policy" | "sovereign-10y" | "fx-usd";
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
  { key: "core-inflation", label: "CORE INFLATION · YOY", seriesSlugs: ["core-cpi"], connectorHint: "Official core CPI or HICP release", acceptedFrequencies: ["monthly", "quarterly"], maximumAgeDays: 130, acceptedSourceTypes: ["official", "international"] },
  { key: "gdp", label: "GDP · CURRENT USD", seriesSlugs: ["gdp-current-usd"], connectorHint: "Comparable nominal GDP series", acceptedFrequencies: ["quarterly"], maximumAgeDays: 200, acceptedSourceTypes: ["official", "international"] },
  { key: "unemployment", label: "UNEMPLOYMENT RATE", seriesSlugs: ["unemployment-rate", "unemployment-total"], connectorHint: "Official labour-market release", acceptedFrequencies: ["monthly", "quarterly"], maximumAgeDays: 130, acceptedSourceTypes: ["official", "international"] },
  { key: "policy", label: "POLICY RATE", seriesSlugs: ["policy-rate"], connectorHint: "Official central-bank rate", acceptedFrequencies: ["daily", "weekly", "monthly"], maximumAgeDays: 35, acceptedSourceTypes: ["official", "international"] },
  { key: "sovereign-10y", label: "10Y SOVEREIGN YIELD", seriesSlugs: ["treasury-10y", "sovereign-10y"], connectorHint: "Official or licensed sovereign-yield source", acceptedFrequencies: ["daily", "weekly", "monthly"], maximumAgeDays: 50, acceptedSourceTypes: ["official", "international", "market"] },
  { key: "fx-usd", label: "FX VS USD", seriesSlugs: ["fx-usd"], connectorHint: "FX series against the U.S. dollar", acceptedFrequencies: ["daily", "weekly"], maximumAgeDays: 10, acceptedSourceTypes: ["official", "international", "market"] },
];
