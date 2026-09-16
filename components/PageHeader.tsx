type PageHeaderProps = { number: string; eyebrow: string; title: string; description?: string; showDivider?: boolean };

export default function PageHeader({ number, eyebrow, title, description, showDivider = true }: PageHeaderProps) {
  return <header className={`${showDivider ? "border-b border-zinc-800" : ""} pb-10 sm:pb-14`}>
    <p className="font-mono text-xs text-zinc-600">{number}</p>
    <p className="mt-5 font-mono text-xs tracking-[0.18em] text-zinc-500">{eyebrow}</p>
    <h1 className="mt-5 text-4xl font-medium tracking-tight sm:text-5xl">{title}</h1>
    {description && <p className="mt-5 max-w-2xl text-base leading-7 text-zinc-400">{description}</p>}
  </header>;
}
