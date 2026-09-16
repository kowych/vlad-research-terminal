export type CoverageState = "LIVE" | "PARTIAL" | "DELAYED" | "MISSING";

export type MetricCoverage = {
  key: "core-inflation" | "gdp" | "unemployment" | "policy" | "sovereign-10y" | "fx-usd";
  label: string;
  status: CoverageState;
  reason: string;
  sourceName?: string;
  sourceType?: "official" | "international" | "market" | "news" | "bootstrap";
  frequency?: "daily" | "weekly" | "monthly" | "quarterly" | "annual" | "event";
  periodStart?: string;
  asOfDate?: string;
};

export type CountryCoverage = {
  iso2: string;
  name: string;
  status: CoverageState;
  liveMetricCount: number;
  metrics: MetricCoverage[];
};

export type CoverageDashboardResponse = {
  generatedAt: string;
  countries: CountryCoverage[];
};
