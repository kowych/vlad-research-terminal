import Link from "next/link";
import LiveClock from "./LiveClock";
import ThemeToggle from "./ThemeToggle";

const links = [
  { href: "/research", label: "Research" }, { href: "/macro", label: "Macro" },
  { href: "/daily", label: "Daily" }, { href: "/positions", label: "Positions" }, { href: "/about", label: "About" },
];

export default function Navbar() {
  return (
    <nav className="sticky top-0 z-50 border-b border-zinc-800 bg-[#0a0a0a]/95 backdrop-blur-sm">
      <div className="mx-auto flex max-w-7xl items-center justify-between gap-6 px-6 py-4 lg:px-8">
        <Link href="/" className="shrink-0 font-mono text-xs tracking-[0.16em] sm:text-sm">MUKLANOVICH / RESEARCH</Link>
        <div className="flex items-center gap-5 sm:gap-8"><div className="hidden gap-5 text-xs text-zinc-400 md:flex lg:gap-7 lg:text-sm">
          {links.map((link) => <Link key={link.href} href={link.href} className="transition-colors hover:text-zinc-100">{link.label}</Link>)}
        </div>
        <ThemeToggle /><LiveClock /></div>
      </div>
    </nav>
  );
}
