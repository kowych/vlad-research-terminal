import Navbar from "@/components/Navbar";

export default function Home() {
  const research = [
    {
      number: "01",
      title: "USD Liquidity Regime",
      description:
        "Dollar liquidity, rates and cross-asset implications.",
      category: "MACRO",
      date: "10 SEP",
    },
    {
      number: "02",
      title: "EUR/USD Mean Reversion",
      description:
        "A quantitative study of mean-reversion behaviour in EUR/USD.",
      category: "FX",
      date: "07 SEP",
    },
    {
      number: "03",
      title: "Japan Intervention Risk",
      description:
        "BOJ policy, yen dynamics and intervention scenarios.",
      category: "MACRO / FX",
      date: "02 SEP",
    },
  ];

  const markets = [
    { name: "DXY", value: "98.42", change: "-0.18%" },
    { name: "GOLD", value: "3,642", change: "+0.72%" },
    { name: "S&P 500", value: "6,512", change: "-0.42%" },
    { name: "BTC", value: "113,420", change: "+1.14%" },
  ];

  return (
    <main className="min-h-screen bg-[#0a0a0a] text-zinc-100">
      
      {/* NAVIGATION */}
      <nav className="border-b border-zinc-800/80">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-5 lg:px-8">
          <div className="font-mono text-sm tracking-wider">
            VLAD / RESEARCH
          </div>

          <div className="hidden items-center gap-8 font-mono text-xs text-zinc-500 sm:flex">
            <a href="#" className="text-zinc-100">
              RESEARCH
            </a>
            <a href="#" className="transition-colors hover:text-zinc-100">
              TRADES
            </a>
            <a href="#" className="transition-colors hover:text-zinc-100">
              MACRO
            </a>
            <a href="#" className="transition-colors hover:text-zinc-100">
              TERMINAL
            </a>
            <a href="#" className="transition-colors hover:text-zinc-100">
              CV
            </a>
          </div>

          <div className="font-mono text-xs text-zinc-600">
            10 SEP 2026
          </div>
        </div>
      </nav>

      {/* HERO */}
      <section className="mx-auto max-w-6xl px-6 py-24 lg:px-8 lg:py-32">
        <p className="font-mono text-xs tracking-[0.2em] text-zinc-500">
          DATA · MARKETS · TRADING · RESEARCH
        </p>

        <h1 className="mt-6 max-w-4xl text-5xl font-medium leading-[1.05] tracking-tight sm:text-6xl lg:text-7xl">
          Independent research
          <br />
          on financial markets.
        </h1>

        <p className="mt-8 max-w-2xl text-base leading-7 text-zinc-500 sm:text-lg">
          A personal research journal covering macroeconomics, trading,
          market psychology, risk and quantitative analysis.
        </p>

        <div className="mt-10 flex gap-4">
          <a
            href="#research"
            className="border border-zinc-700 px-5 py-3 font-mono text-xs tracking-wider transition-colors hover:border-zinc-400"
          >
            VIEW RESEARCH →
          </a>

          <a
            href="#markets"
            className="px-5 py-3 font-mono text-xs tracking-wider text-zinc-500 transition-colors hover:text-zinc-100"
          >
            MARKET DATA
          </a>
        </div>
      </section>

      {/* RESEARCH */}
      <section
        id="research"
        className="mx-auto max-w-6xl px-6 pb-24 lg:px-8"
      >
        <div className="mb-6 flex items-end justify-between border-b border-zinc-800 pb-4">
          <div>
            <p className="font-mono text-xs text-zinc-600">01</p>
            <h2 className="mt-2 font-mono text-sm tracking-wider">
              LATEST RESEARCH
            </h2>
          </div>

          <span className="font-mono text-xs text-zinc-600">
            2026
          </span>
        </div>

        <div>
          {research.map((item) => (
            <article
              key={item.number}
              className="group grid gap-4 border-b border-zinc-800 py-7 transition-colors hover:border-zinc-600 sm:grid-cols-[48px_1fr_120px_80px]"
            >
              <span className="font-mono text-xs text-zinc-600">
                {item.number}
              </span>

              <div>
                <h3 className="text-xl font-medium tracking-tight transition-colors group-hover:text-zinc-300">
                  {item.title}
                </h3>

                <p className="mt-2 max-w-xl text-sm leading-6 text-zinc-600">
                  {item.description}
                </p>
              </div>

              <span className="font-mono text-[10px] tracking-wider text-zinc-600 sm:pt-1">
                {item.category}
              </span>

              <span className="font-mono text-[10px] text-zinc-600 sm:pt-1">
                {item.date}
              </span>
            </article>
          ))}
        </div>
      </section>

      {/* CURRENT FOCUS */}
      <section className="mx-auto max-w-6xl px-6 pb-24 lg:px-8">
        <div className="border-y border-zinc-800 py-8">
          <p className="font-mono text-xs tracking-wider text-zinc-600">
            CURRENT FOCUS
          </p>

          <div className="mt-5 flex flex-wrap gap-x-8 gap-y-3 font-mono text-sm text-zinc-400">
            <span>USD LIQUIDITY</span>
            <span>FED POLICY</span>
            <span>GOLD / REAL YIELDS</span>
            <span>JPY INTERVENTION RISK</span>
          </div>
        </div>
      </section>

      {/* MARKET OVERVIEW */}
      <section
        id="markets"
        className="mx-auto max-w-6xl px-6 pb-32 lg:px-8"
      >
        <div className="mb-6 flex items-end justify-between border-b border-zinc-800 pb-4">
          <div>
            <p className="font-mono text-xs text-zinc-600">02</p>
            <h2 className="mt-2 font-mono text-sm tracking-wider">
              MARKET OVERVIEW
            </h2>
          </div>

          <span className="font-mono text-xs text-zinc-600">
            DELAYED
          </span>
        </div>

        <div className="grid border-l border-t border-zinc-800 sm:grid-cols-2 lg:grid-cols-4">
          {markets.map((market) => (
            <div
              key={market.name}
              className="border-b border-r border-zinc-800 p-6"
            >
              <p className="font-mono text-xs text-zinc-600">
                {market.name}
              </p>

              <div className="mt-6 flex items-end justify-between">
                <span className="text-2xl tracking-tight">
                  {market.value}
                </span>

                <span className="font-mono text-xs text-zinc-500">
                  {market.change}
                </span>
              </div>
            </div>
          ))}
        </div>

        <p className="mt-4 font-mono text-[10px] text-zinc-700">
          MARKET DATA · STATIC DEMO · LIVE DATA WILL BE CONNECTED LATER
        </p>
      </section>

      {/* FOOTER */}
      <footer className="border-t border-zinc-800">
        <div className="mx-auto flex max-w-6xl flex-col justify-between gap-4 px-6 py-8 font-mono text-xs text-zinc-600 sm:flex-row lg:px-8">
          <span>VLAD / RESEARCH</span>
          <span>DATA · MARKETS · TRADING</span>
        </div>
      </footer>
    </main>
  );
}