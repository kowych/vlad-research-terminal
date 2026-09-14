import Link from "next/link";
import EmptyArchive from "@/components/EmptyArchive";
import PageHeader from "@/components/PageHeader";
import { dailyNotes } from "@/lib/content";
export const metadata = { title: "Daily" };
export default function DailyPage() { return <section className="page-shell"><PageHeader number="02" eyebrow="MARKET JOURNAL" title="Daily" description="Concise market notes, observations and changes in the active macro narrative." /><div className="mt-10">{dailyNotes.length ? dailyNotes.map((note) => <Link key={note.slug} href={`/daily/${note.slug}`} className="archive-row"><span>{note.publishedAt}</span><div><h2>{note.title}</h2><p>{note.summary}</p></div><span>{note.tags.join(" / ")}</span></Link>) : <EmptyArchive label="NO DAILY NOTES YET" detail="The daily journal is reserved for time-sensitive observations that sit between longer research papers." />}</div></section>; }
