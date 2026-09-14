"use client";

import { useEffect, useState } from "react";

type Theme = "light" | "dark";

function applyTheme(theme: Theme) {
  document.documentElement.dataset.theme = theme;
  document.documentElement.style.colorScheme = theme;
}

export default function ThemeToggle() {
  const [theme, setTheme] = useState<Theme>(() => {
    if (typeof window === "undefined") return "dark";
    const savedTheme = window.localStorage.getItem("muklanovich-theme") as Theme | null;
    return savedTheme ?? (window.matchMedia("(prefers-color-scheme: light)").matches ? "light" : "dark");
  });

  useEffect(() => {
    applyTheme(theme);
  }, [theme]);

  function toggleTheme() {
    const nextTheme = theme === "dark" ? "light" : "dark";
    setTheme(nextTheme);
    window.localStorage.setItem("muklanovich-theme", nextTheme);
    applyTheme(nextTheme);
  }

  return <button type="button" onClick={toggleTheme} className="theme-toggle" aria-label="Toggle colour theme">
    <span aria-hidden="true">{theme === "dark" ? "☀" : "◐"}</span>
    <span className="hidden sm:inline">THEME</span>
  </button>;
}
