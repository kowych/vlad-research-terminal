import Link from "next/link";
import EmptyArchive from "@/components/EmptyArchive";
import PageHeader from "@/components/PageHeader";
import { researchPosts } from "@/lib/content";

export const metadata = { title: "Research" };
export default function ResearchPage() {
  return <section className="page-shell"><PageHeader number="01" eyebrow="RESEARCH ARCHIVE" title="Research" description="Long-form market and macro research. Each paper records the thesis, catalysts, invalidation and status." />
    <div className="mt-10">{researchPosts.length ? researchPosts.map((post) => <Link key={post.slug} href={`/research/${post.slug}`} className="archive-row"><span>{post.status}</span><div><h2>{post.title}</h2><p>{post.summary}</p></div><span>{post.category}<br />{post.publishedAt}</span></Link>) : <EmptyArchive label="NO PAPERS PUBLISHED" detail="New research will appear here with a clear thesis, scenario framework, supporting data and explicit invalidation conditions." />}</div>
  </section>;
}
