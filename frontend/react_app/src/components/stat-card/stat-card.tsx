/**
 * StatCard — single KPI tile for the landing page.
 * Shows a large number, label, and optional description.
 */
import React from "react";

interface Props {
  value: number | string;
  label: string;
  description?: string;
  accent?: "blue" | "emerald" | "violet" | "amber";
  loading?: boolean;
}

const ACCENTS = {
  blue: { bg: "bg-blue-50", text: "text-blue-600", border: "border-blue-100" },
  emerald: {
    bg: "bg-emerald-50",
    text: "text-emerald-600",
    border: "border-emerald-100",
  },
  violet: {
    bg: "bg-violet-50",
    text: "text-violet-600",
    border: "border-violet-100",
  },
  amber: {
    bg: "bg-amber-50",
    text: "text-amber-600",
    border: "border-amber-100",
  },
};

function fmt(v: number | string): string {
  if (typeof v === "string") return v;
  return v >= 1000 ? `${(v / 1000).toFixed(1)}k` : String(v);
}

export default function StatCard({
  value,
  label,
  description,
  accent = "blue",
  loading = false,
}: Props) {
  const a = ACCENTS[accent];

  return (
    <div
      className={`rounded-xl border ${a.border} ${a.bg} px-5 py-4 flex flex-col gap-1`}
    >
      {loading ? (
        <div className="h-9 w-20 rounded-lg bg-slate-200 animate-pulse" />
      ) : (
        <p className={`text-3xl font-bold tabular-nums ${a.text}`}>
          {fmt(value)}
        </p>
      )}
      <p className="text-sm font-semibold text-slate-700">{label}</p>
      {description && <p className="text-xs text-slate-500">{description}</p>}
    </div>
  );
}
