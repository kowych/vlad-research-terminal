export type ResearchPost = { slug: string; title: string; summary: string; category: string; publishedAt: string; status: "ACTIVE" | "UPDATED" | "CLOSED"; thesis: string; catalysts: string[]; invalidation: string; };
export type DailyNote = { slug: string; title: string; summary: string; publishedAt: string; tags: string[]; };
export type Position = { instrument: string; direction: "LONG" | "SHORT"; horizon: string; risk: string; status: "ACTIVE" | "WATCHING" | "CLOSED"; thesis: string; invalidation: string; };
// Add an entry to publish it locally. It automatically appears in its archive.
export const researchPosts: ResearchPost[] = [];
export const dailyNotes: DailyNote[] = [];
export const positions: Position[] = [];
