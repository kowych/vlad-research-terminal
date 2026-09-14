# Muklanovich Research

An independent research desk for macroeconomics, markets and quantitative analysis.

## Local development

```bash
npm run dev
```

Open the local URL printed by Next.js.

## Publishing content

The first release uses a typed local catalogue at `lib/content.ts`. Add an entry to one of these arrays:

- `researchPosts` for a long-form paper;
- `dailyNotes` for a market journal entry;
- `positions` for a public position with risk and invalidation, without P/L.

Posts are then shown in their archive automatically. A research entry also receives a static page at `/research/[slug]`; daily entries appear at `/daily/[slug]`.

### Research template

```ts
{
  slug: "descriptive-url-slug",
  title: "Paper title",
  summary: "One-sentence abstract.",
  category: "MACRO / FX",
  publishedAt: "14 SEP 2026",
  status: "ACTIVE",
  thesis: "The central view and reasoning.",
  catalysts: ["What can move the thesis", "A second catalyst"],
  invalidation: "What would make the thesis wrong.",
}
```

This is intentionally local and dependency-free. Once publishing needs exceed a compact catalogue, the presentation layer can be kept while the source moves to MDX or a CMS.

## Macro data platform

The initial country registry is in `data/countries.ts`. It drives the Macro table today and will drive the globe markers later. The scalable PostgreSQL model and source rules are documented in `database/`.

For the live United States desk, copy `.env.local.example` to `.env.local`. This connection string is server-only; do not use a `NEXT_PUBLIC_` prefix.

Live country desks use the dynamic `/macro/[country]` route. `/macro/us` is currently published. Japan raw data has been ingested for connector validation but is deliberately withheld from the live desk because the selected FRED series are stale; add a current primary-source connector and pass freshness validation before publishing it.
