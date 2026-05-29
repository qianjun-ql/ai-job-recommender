/**
 * JobCard — compact result card with match-score badge and skill tags.
 */
import React from "react";
import type { JobMatchResponse } from "@/api/client";
import { scoreBadge, pill } from "@/styles/colors";

interface Props {
  job: JobMatchResponse;
}

export default function JobCard({ job }: Props) {
  const pct = Math.round(job.match_score * 100);

  return (
    <div
      className="group relative flex flex-col rounded-xl border border-slate-200 bg-white p-5 shadow-sm
                    transition hover:shadow-md hover:-translate-y-0.5"
    >
      {/* Score badge — top-right */}
      <span
        className={`absolute right-4 top-4 rounded-full px-2.5 py-0.5 text-xs font-semibold tabular-nums ${scoreBadge(pct)}`}
      >
        {pct}%
      </span>

      {/* Titles */}
      <div className="pr-14 mb-3">
        <h3 className="font-semibold text-slate-900 text-sm leading-snug">
          {job.title}
        </h3>
        <p className="mt-0.5 text-xs text-slate-500">{job.role}</p>
        {job.location && (
          <p className="mt-0.5 flex items-center gap-1 text-xs text-slate-400">
            <svg
              className="w-3 h-3 shrink-0"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z"
              />
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M15 11a3 3 0 11-6 0 3 3 0 016 0z"
              />
            </svg>
            {job.location}
          </p>
        )}
      </div>

      {/* Snippet */}
      {job.snippet && (
        <p className="mb-3 text-xs text-slate-500 line-clamp-2 leading-relaxed">
          {job.snippet}
        </p>
      )}

      {/* Match score bar */}
      <div className="mb-3">
        <div className="h-1.5 w-full rounded-full bg-slate-100 overflow-hidden">
          <div
            className="h-full rounded-full transition-all"
            style={{
              width: `${pct}%`,
              background:
                pct >= 75 ? "#10b981" : pct >= 50 ? "#f59e0b" : "#f43f5e",
            }}
          />
        </div>
      </div>

      {/* Skills */}
      {job.skills.length > 0 && (
        <div className="flex flex-wrap gap-1 mt-auto">
          {job.skills.slice(0, 7).map((skill) => (
            <span
              key={skill}
              className={`rounded-full px-2 py-0.5 text-[11px] font-medium ${pill.neutral}`}
            >
              {skill}
            </span>
          ))}
          {job.skills.length > 7 && (
            <span className="text-[11px] text-slate-400 self-center">
              +{job.skills.length - 7}
            </span>
          )}
        </div>
      )}
    </div>
  );
}
