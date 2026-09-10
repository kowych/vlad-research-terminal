import LiveClock from "./LiveClock";

export default function Navbar() {
  return (
    <nav className="sticky top-0 z-50 flex items-center justify-between border-b border-zinc-800 bg-[#0a0a0a]/95 px-8 py-5 backdrop-blur-sm">
      <div className="font-mono text-sm tracking-wider">
        VLAD / RESEARCH
      </div>

      <div className="flex items-center gap-8">
        <div className="flex gap-8 text-sm text-zinc-400">
          <a href="/">Research</a>
          <a href="/trades">Trades</a>
          <a href="/macro">Macro</a>
          <a href="/cv">CV</a>
        </div>

        <LiveClock />
      </div>
    </nav>
  );
}