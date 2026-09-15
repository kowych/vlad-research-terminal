"use client";

import { useEffect } from "react";

export default function GlobalError({ error, reset }: { error: Error & { digest?: string }; reset: () => void }) {
  useEffect(() => {
    console.error(error);
  }, [error]);

  return (
    <section className="page-shell">
      <p className="font-mono text-xs tracking-[0.18em] text-zinc-500">UNEXPECTED ERROR</p>
      <h1 className="mt-5 text-4xl font-medium tracking-tight sm:text-5xl">The desk could not be loaded.</h1>
      <p className="mt-5 max-w-xl text-base leading-7 text-zinc-400">No research data was changed. You can safely try the request again.</p>
      <button type="button" onClick={reset} className="terminal-link mt-8">TRY AGAIN →</button>
    </section>
  );
}
