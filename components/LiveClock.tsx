"use client";

import { useEffect, useState } from "react";

const timeZone = "Europe/Warsaw";

export default function LiveClock() {
  const [now, setNow] = useState(new Date());

  useEffect(() => {
    const timer = setInterval(() => {
      setNow(new Date());
    }, 1000);

    return () => clearInterval(timer);
  }, []);

  const date = now.toLocaleDateString("en-GB", {
    day: "2-digit",
    month: "short",
    year: "numeric",
    timeZone,
  });

  const time = now.toLocaleTimeString("en-GB", {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: false,
    timeZone,
  });
  const zone = new Intl.DateTimeFormat("en-GB", { timeZone, timeZoneName: "short" })
    .formatToParts(now)
    .find((part) => part.type === "timeZoneName")?.value ?? "CET";

  return (
    <div className="hidden sm:block text-right font-mono text-xs tracking-wider text-zinc-400">
      <div>{date}</div>
      <div className="text-zinc-600">{time} {zone}</div>
    </div>
  );
}
