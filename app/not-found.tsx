import Link from "next/link";

export default function NotFound() {
  return (
    <section className="page-shell">
      <p className="font-mono text-xs tracking-[0.18em] text-zinc-500">404 · NOT FOUND</p>
      <h1 className="mt-5 text-4xl font-medium tracking-tight sm:text-5xl">This page does not exist.</h1>
      <p className="mt-5 max-w-xl text-base leading-7 text-zinc-400">The requested research entry or country desk is unavailable.</p>
      <Link href="/" className="terminal-link mt-8">RETURN HOME →</Link>
    </section>
  );
}
