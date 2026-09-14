export type MacroPoint = { date: string; value: number };
export type MacroSeries = {
  slug: string;
  name: string;
  unit: string;
  sourceName: string;
  freshness: "CURRENT" | "DELAYED" | "ANNUAL BASELINE";
  latest: MacroPoint;
  asOfDate: string;
  ingestedAt: string;
  change?: number;
  points: MacroPoint[];
};
export type MacroEvent = { id: string; title: string; eventType: string; materiality: number; score?: number; impactScope: "direct" | "regional" | "spillover"; occurredAt: string; sourceName: string; originalUrl: string; indicators: string[] };
export type CalendarEvent = { id: string; title: string; category?: string; scheduledAt: string; importance: number; forecast?: string; previous?: string; currency?: string; sourceName?: string; sourceUrl?: string };
export type UsMacroDesk = { generatedAt: string; regime: string; rationale: string; series: MacroSeries[]; events: MacroEvent[]; calendar: CalendarEvent[] };
