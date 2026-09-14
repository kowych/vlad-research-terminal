import Link from "next/link";
import { dailyNotes, positions, researchPosts } from "@/lib/content";

const currentFocus = ["USD LIQUIDITY", "FED POLICY", "GOLD / REAL YIELDS", "JPY INTERVENTION RISK"];

export default function Home() {
  return <>
    <section className="mx-auto max-w-7xl px-6 py-24 lg:px-8 lg:py-32">
      <p className="font-mono text-xs tracking-[0.2em] text-zinc-400">DATA · MARKETS · TRADING · RESEARCH</p>
      <h1 className="mt-6 max-w-4xl text-5xl font-medium leading-[1.02] tracking-tight sm:text-6xl lg:text-7xl">Muklanovich Research</h1>
      <p className="mt-6 max-w-2xl text-base leading-7 text-zinc-400 sm:text-lg">Independent research on macroeconomics, market regimes and quantitative frameworks.</p>
      <div className="mt-10 flex flex-wrap gap-3"><Link href="/research" className="terminal-link">VIEW RESEARCH →</Link><Link href="/macro" className="terminal-link">EXPLORE MACRO →</Link><Link href="/positions" className="terminal-link">OPEN POSITIONS →</Link></div>
    </section>
    <section className="mx-auto max-w-7xl px-6 pb-24 lg:px-8">
      <div className="section-label"><span>01</span><h2>LATEST RESEARCH</h2><Link href="/research">VIEW ALL →</Link></div>
      {researchPosts.length ? <div>{researchPosts.slice(0, 3).map((post) => <Link className="archive-row" key={post.slug} href={`/research/${post.slug}`}><span>{post.status}</span><div><h3>{post.title}</h3><p>{post.summary}</p></div><span>{post.category}</span></Link>)}</div> : <p className="empty-line">FIRST RESEARCH PAPER — IN PREPARATION</p>}
    </section>
    <section className="mx-auto max-w-7xl px-6 pb-24 lg:px-8"><div className="focus-strip"><p>CURRENT FOCUS</p><div>{currentFocus.map((item) => <span key={item}>{item}</span>)}</div></div></section>
    <section className="mx-auto max-w-7xl px-6 pb-24 lg:px-8"><div className="section-label"><span>02</span><h2>DESK STATUS</h2></div><div className="grid border-l border-t border-zinc-800 sm:grid-cols-3"><div className="metric"><p>RESEARCH</p><strong>{researchPosts.length.toString().padStart(2, "0")}</strong><span>PUBLISHED PAPERS</span></div><div className="metric"><p>DAILY</p><strong>{dailyNotes.length.toString().padStart(2, "0")}</strong><span>MARKET NOTES</span></div><div className="metric"><p>POSITIONS</p><strong>{positions.filter((position) => position.status === "ACTIVE").length.toString().padStart(2, "0")}</strong><span>ACTIVE IDEAS</span></div></div></section>
  </>;
}
