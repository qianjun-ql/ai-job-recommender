/**
 * Centralized theme colors.
 *
 * Usage:
 *   import { chart, semantic, difficulty } from '@/styles/colors'
 *
 * For Tailwind classes use the `tw` map.
 * For Recharts / inline styles use the `chart` / `brand` hex values.
 */

// ─── Accent palette (indigo/purple/pink/emerald/amber — used in new UI) ────────

export const accent = {
  indigo: "#6366f1",
  indigoBg: "#eef2ff",
  purple: "#8b5cf6",
  purpleBg: "#f5f3ff",
  pink: "#ec4899",
  pinkBg: "rgba(236,72,153,0.06)",
  emerald: "#10b981",
  emeraldBg: "#ecfdf5",
  amber: "#f97316",
  amberBg: "#fff7ed",
  yellow: "#eab308",
} as const;

// ─── Per-role colors (match RoleCompareChart assignments) ────────────────────

export const roleColors: Record<string, string> = {
  "AI Engineer": accent.indigo,
  "ML Engineer": accent.emerald,
  "Data Scientist": accent.amber,
  "Data Engineer": accent.pink,
  SWE: accent.yellow,
};

// ─── Floating background tag colors ──────────────────────────────────────────

export const floatingTagColors = [
  accent.indigo,
  accent.purple,
  accent.pink,
  accent.emerald,
  accent.amber,
] as const;

// ─── Brand palette (hex) ──────────────────────────────────────────────────────

export const brand = {
  50: "#eff6ff",
  100: "#dbeafe",
  200: "#bfdbfe",
  300: "#93c5fd",
  400: "#60a5fa",
  500: "#3b82f6",
  600: "#2563eb",
  700: "#1d4ed8",
  800: "#1e40af",
  900: "#1e3a8a",
} as const;

// ─── Semantic colors (hex, for Recharts / SVG / inline styles) ────────────────

export const semantic = {
  matched: "#10b981", // emerald-500
  missing: "#f43f5e", // rose-500
  neutral: "#94a3b8", // slate-400
  warning: "#f59e0b", // amber-500
} as const;

// ─── Chart bar colors ─────────────────────────────────────────────────────────

export const chart = {
  bars: [
    brand[600],
    brand[500],
    brand[400],
    brand[300],
    brand[700],
    brand[800],
    "#6366f1", // indigo-500
    "#8b5cf6", // violet-500
  ],
  matched: semantic.matched,
  missing: semantic.missing,
} as const;

// ─── Tailwind class maps (for JSX className usage) ────────────────────────────

/** Score badge classes based on match percentage bucket */
export const scoreBadge = (pct: number): string => {
  if (pct >= 75)
    return "bg-emerald-100 text-emerald-700 ring-1 ring-emerald-200";
  if (pct >= 50) return "bg-amber-100 text-amber-700 ring-1 ring-amber-200";
  return "bg-rose-100 text-rose-700 ring-1 ring-rose-200";
};

/** Difficulty badge classes */
export const difficultyBadge: Record<string, string> = {
  beginner: "bg-emerald-50 text-emerald-700 ring-1 ring-emerald-200",
  intermediate: "bg-amber-50 text-amber-700 ring-1 ring-amber-200",
  advanced: "bg-rose-50 text-rose-700 ring-1 ring-rose-200",
};

/** Skill pill classes */
export const pill = {
  matched: "bg-emerald-50 text-emerald-700 ring-1 ring-emerald-100",
  missing: "bg-rose-50 text-rose-600 ring-1 ring-rose-100",
  neutral: "bg-slate-100 text-slate-600",
  primary: "bg-blue-50 text-blue-700 ring-1 ring-blue-100",
} as const;
