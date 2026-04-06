"use client";

import { MoonStar, SunMedium } from "lucide-react";
import { useTheme } from "next-themes";
import { useSyncExternalStore } from "react";

type ThemeToggleProps = {
  className?: string;
};

export function ThemeToggle({ className = "" }: ThemeToggleProps) {
  const { resolvedTheme, setTheme } = useTheme();
  const mounted = useSyncExternalStore(
    () => () => undefined,
    () => true,
    () => false
  );

  const isDark = mounted ? resolvedTheme === "dark" : false;

  return (
    <button
      type="button"
      onClick={() => setTheme(isDark ? "light" : "dark")}
      aria-label={mounted ? `Switch to ${isDark ? "light" : "dark"} mode` : "Toggle theme"}
      aria-pressed={isDark}
      className={`group relative inline-flex h-12 w-[92px] items-center rounded-full border border-slate-300/80 bg-white/80 p-1 text-slate-700 shadow-[0_12px_30px_rgba(15,23,42,0.10)] backdrop-blur transition duration-500 hover:border-cyan-300 hover:shadow-[0_16px_36px_rgba(14,165,233,0.18)] dark:border-white/12 dark:bg-slate-950/70 dark:text-slate-100 dark:shadow-[0_16px_42px_rgba(0,0,0,0.28)] dark:hover:border-cyan-300/50 ${className}`}
    >
      <span
        className={`absolute left-1 top-1 flex h-10 w-10 items-center justify-center rounded-full bg-[linear-gradient(135deg,_#f8fafc,_#cbd5e1)] shadow-[0_10px_18px_rgba(15,23,42,0.14)] transition-transform duration-500 dark:bg-[linear-gradient(135deg,_#38bdf8,_#22c55e)] dark:shadow-[0_10px_24px_rgba(56,189,248,0.24)] ${
          isDark ? "translate-x-10" : "translate-x-0"
        }`}
      >
        <SunMedium
          className={`h-4 w-4 transition-all duration-500 ${
            isDark ? "rotate-90 scale-75 opacity-0" : "rotate-0 scale-100 opacity-100"
          } text-amber-500`}
        />
        <MoonStar
          className={`absolute h-4 w-4 transition-all duration-500 ${
            isDark ? "rotate-0 scale-100 opacity-100" : "-rotate-90 scale-75 opacity-0"
          } text-slate-950`}
        />
      </span>

      <span className="sr-only">Toggle color theme</span>
      <span
        className={`ml-3 text-[10px] font-semibold uppercase tracking-[0.24em] transition-opacity duration-300 ${
          isDark ? "opacity-0" : "opacity-100"
        }`}
      >
        Light
      </span>
      <span
        className={`ml-auto mr-3 text-[10px] font-semibold uppercase tracking-[0.24em] transition-opacity duration-300 ${
          isDark ? "opacity-100" : "opacity-0"
        }`}
      >
        Dark
      </span>
    </button>
  );
}
