/**
 * GapChart — skill gap summary with a segmented progress bar + matched/missing pill lists.
 */
import React from "react";
import { semantic, pill } from "@/styles/colors";

interface Props {
  matchedSkills: string[];
  missingSkills: string[];
  matchScore: number;
}

export default function GapChart({
  matchedSkills,
  missingSkills,
  matchScore,
}: Props) {
  const pct = Math.round(matchScore * 100);
  const total = matchedSkills.length + missingSkills.length;

  const scoreColor =
    pct >= 75
      ? "text-emerald-600"
      : pct >= 50
        ? "text-amber-600"
        : "text-rose-600";

  return (
    <div className="rounded-xl border border-slate-200 bg-white shadow-sm overflow-hidden">
      {/* Header strip */}
      <div className="border-b border-slate-100 px-6 py-4 flex flex-wrap items-center gap-6">
        <div>
          <p className="text-xs font-semibold uppercase tracking-widest text-slate-400 mb-0.5">
            Match Score
          </p>
          <p className={`text-3xl font-bold tabular-nums ${scoreColor}`}>
            {pct}
            <span className="text-base font-medium text-slate-400">%</span>
          </p>
        </div>
        <div className="h-10 w-px bg-slate-100 hidden sm:block" />
        <div>
          <p className="text-xs font-semibold uppercase tracking-widest text-slate-400 mb-0.5">
            Matched
          </p>
          <p className="text-3xl font-bold text-emerald-600 tabular-nums">
            {matchedSkills.length}
          </p>
        </div>
        <div className="h-10 w-px bg-slate-100 hidden sm:block" />
        <div>
          <p className="text-xs font-semibold uppercase tracking-widest text-slate-400 mb-0.5">
            Missing
          </p>
          <p className="text-3xl font-bold text-rose-500 tabular-nums">
            {missingSkills.length}
          </p>
        </div>
      </div>

      {/* Segmented bar */}
      {total > 0 && (
        <div className="px-6 py-3 bg-slate-50 border-b border-slate-100">
          <div className="flex h-2 w-full rounded-full overflow-hidden gap-0.5">
            <div
              className="rounded-l-full transition-all"
              style={{
                width: `${(matchedSkills.length / total) * 100}%`,
                backgroundColor: semantic.matched,
              }}
            />
            <div
              className="rounded-r-full transition-all"
              style={{
                width: `${(missingSkills.length / total) * 100}%`,
                backgroundColor: semantic.missing,
              }}
            />
          </div>
          <div className="flex justify-between mt-1.5 text-[10px] font-medium text-slate-400">
            <span style={{ color: semantic.matched }}>▪ Matched</span>
            <span style={{ color: semantic.missing }}>Missing ▪</span>
          </div>
        </div>
      )}

      {/* Pill lists */}
      <div className="grid sm:grid-cols-2 divide-y sm:divide-y-0 sm:divide-x divide-slate-100">
        <div className="px-6 py-4">
          <p className="mb-2 text-xs font-semibold uppercase tracking-widest text-emerald-600">
            You have ({matchedSkills.length})
          </p>
          {matchedSkills.length > 0 ? (
            <div className="flex flex-wrap gap-1.5">
              {matchedSkills.map((s) => (
                <span
                  key={s}
                  className={`rounded-full px-2.5 py-0.5 text-xs font-medium ${pill.matched}`}
                >
                  {s}
                </span>
              ))}
            </div>
          ) : (
            <p className="text-xs text-slate-400">No matching skills found</p>
          )}
        </div>

        <div className="px-6 py-4">
          <p className="mb-2 text-xs font-semibold uppercase tracking-widest text-rose-500">
            To learn ({missingSkills.length})
          </p>
          {missingSkills.length > 0 ? (
            <div className="flex flex-wrap gap-1.5">
              {missingSkills.map((s) => (
                <span
                  key={s}
                  className={`rounded-full px-2.5 py-0.5 text-xs font-medium ${pill.missing}`}
                >
                  {s}
                </span>
              ))}
            </div>
          ) : (
            <p className="text-xs text-slate-400">No gaps — great coverage!</p>
          )}
        </div>
      </div>
    </div>
  );
}
