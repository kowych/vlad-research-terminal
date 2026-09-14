import { notFound } from "next/navigation";
import PageHeader from "@/components/PageHeader";
import { researchPosts } from "@/lib/content";

export function generateStaticParams() { return researchPosts.map(({ slug }) => ({ slug })); }
export default async function ResearchPostPage({ params }: { params: Promise<{ slug: string }> }) {
  const { slug } = await params;
  const post = researchPosts.find((item) => item.slug === slug);
  if (!post) notFound();
  return <article className="page-shell"><PageHeader number={post.status} eyebrow={`${post.category} · ${post.publishedAt}`} title={post.title} description={post.summary} />
    <div className="article-grid"><section><p className="article-label">CORE THESIS</p><p className="article-copy">{post.thesis}</p></section><section><p className="article-label">CATALYSTS</p><ul className="article-list">{post.catalysts.map((catalyst) => <li key={catalyst}>{catalyst}</li>)}</ul></section><section><p className="article-label">INVALIDATION</p><p className="article-copy">{post.invalidation}</p></section></div>
  </article>;
}
