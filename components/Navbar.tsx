export default function Navbar() {
  return (
    <nav className="flex items-center justify-between border-b border-zinc-800 px-8 py-5">
      <div className="font-mono text-sm tracking-wider">
        VLAD / RESEARCH
      </div>

      <div className="flex gap-8 text-sm text-zinc-400">
        <a href="/">Research</a>
        <a href="/trades">Trades</a>
        <a href="/macro">Macro</a>
        <a href="/cv">CV</a>
      </div>
    </nav>
  );
}