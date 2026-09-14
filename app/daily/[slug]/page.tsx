import { notFound } from "next/navigation";
import PageHeader from "@/components/PageHeader";
import { dailyNotes } from "@/lib/content";
export function generateStaticParams() { return dailyNotes.map(({ slug }) => ({ slug })); }
export default async function DailyPostPage({ params }: { params: Promise<{ slug: string }> }) { const { slug } = await params; const note = dailyNotes.find((item) => item.slug === slug); if (!note) notFound(); return <article className="page-shell"><PageHeader number="DAILY" eyebrow={`${note.tags.join(" / ")} · ${note.publishedAt}`} title={note.title} description={note.summary} /><p className="mt-10 max-w-2xl text-base leading-8 text-zinc-400">Add the complete note body to the content model when publishing this entry.</p></article>; }
