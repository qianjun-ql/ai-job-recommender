/**
 * AnalyzePage — skill input form + job matches + gap chart + project recommendations.
 */
import React, { useEffect, useState } from "react";
import SkillInput from "@/components/skill-input/skill-input";
import JobCard from "@/components/job-card/job-card";
import GapChart from "@/components/gap-chart/gap-chart";
import ProjectCard from "@/components/project-card/project-card";
import { mlApi, type AnalyzeResponse } from "@/api/client";

type ViewState = "idle" | "loading" | "results" | "error";

interface Props {
  /** Skills pre-extracted from a JD on the landing page. */
  prefillSkills?: string[];
}

function SectionHeading({
  children,
  count,
}: {
  children: React.ReactNode;
  count?: number;
}) {
  return (
    <div className="flex items-center gap-3 mb-4">
      <h2 className="text-sm font-bold uppercase tracking-widest text-slate-500">
        {children}
      </h2>
      {count !== undefined && (
        <span className="rounded-full bg-blue-50 px-2.5 py-0.5 text-xs font-semibold text-blue-600">
          {count}
        </span>
      )}
      <div className="flex-1 h-px bg-slate-100" />
    </div>
  );
}

export default function AnalyzePage({ prefillSkills }: Props) {
  const [skills, setSkills] = useState<string[]>(prefillSkills ?? []);
  const [role, setRole] = useState("");
  const [viewState, setViewState] = useState<ViewState>("idle");
  const [result, setResult] = useState<AnalyzeResponse | null>(null);
  const [errorMsg, setErrorMsg] = useState("");

  // When the user arrives from the JD check flow, prefill is non-empty.
  useEffect(() => {
    if (prefillSkills && prefillSkills.length > 0) {
      setSkills(prefillSkills);
    }
  }, [prefillSkills]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (skills.length === 0) return;

    setViewState("loading");
    setErrorMsg("");

    try {
      const data = await mlApi.analyze({
        skills,
        target_role: role || undefined,
      });
      setResult(data);
      setViewState("results");
    } catch (err: unknown) {
      setErrorMsg(
        err instanceof Error
          ? err.message
          : "Request failed. Make sure the API server is running.",
      );
      setViewState("error");
    }
  };

  return (
    <div className="space-y-10">
      {/* Input card */}
      <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
        <div className="mb-6">
          <h2 className="text-lg font-bold text-slate-900">Skill Analysis</h2>
          <p className="mt-1 text-sm text-slate-500">
            Enter your skills and target role to find matching jobs, identify
            gaps, and get personalised project recommendations.
          </p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-6">
          <SkillInput
            skills={skills}
            role={role}
            onSkillsChange={setSkills}
            onRoleChange={setRole}
          />

          <button
            type="submit"
            disabled={skills.length === 0 || viewState === "loading"}
            className="w-full rounded-lg bg-blue-600 py-3 text-sm font-semibold text-white shadow-sm
                       hover:bg-blue-700 disabled:opacity-40 disabled:cursor-not-allowed transition-colors
                       flex items-center justify-center gap-2"
          >
            {viewState === "loading" ? (
              <>
                <span className="w-4 h-4 rounded-full border-2 border-blue-200 border-t-white animate-spin" />
                Analyzing…
              </>
            ) : (
              <>
                <svg
                  className="w-4 h-4"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2.5"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    d="M21 21l-4.35-4.35M11 19a8 8 0 100-16 8 8 0 000 16z"
                  />
                </svg>
                Analyze Skills
              </>
            )}
          </button>
        </form>
      </div>

      {/* Error */}
      {viewState === "error" && (
        <div className="flex items-start gap-3 rounded-lg border border-rose-200 bg-rose-50 px-4 py-3">
          <svg
            className="w-4 h-4 text-rose-500 shrink-0 mt-0.5"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            viewBox="0 0 24 24"
          >
            <circle cx="12" cy="12" r="10" />
            <path strokeLinecap="round" d="M12 8v4m0 4h.01" />
          </svg>
          <p className="text-sm text-rose-700">{errorMsg}</p>
        </div>
      )}

      {/* Results */}
      {viewState === "results" && result && (
        <div className="space-y-10 animate-in fade-in duration-300">
          {/* Gap analysis */}
          <section>
            <SectionHeading>Skill Gap Analysis</SectionHeading>
            <GapChart
              matchedSkills={result.matched_skills}
              missingSkills={result.missing_skills}
              matchScore={result.match_score}
            />
          </section>

          {/* Top matching jobs */}
          {result.top_jobs.length > 0 && (
            <section>
              <SectionHeading count={result.top_jobs.length}>
                Best-Matched Jobs
              </SectionHeading>
              <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
                {result.top_jobs.map((job) => (
                  <JobCard key={job.job_id} job={job} />
                ))}
              </div>
            </section>
          )}

          {/* Project recommendations */}
          {result.projects.length > 0 && (
            <section>
              <SectionHeading count={result.projects.length}>
                Recommended Projects
              </SectionHeading>
              <p className="text-sm text-slate-500 mb-4 -mt-1">
                Portfolio projects to close your skill gaps — each completable
                in ≤40 hours and deployable to GitHub.
              </p>
              <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
                {result.projects.map((project, i) => (
                  <ProjectCard key={i} project={project} index={i} />
                ))}
              </div>
            </section>
          )}
        </div>
      )}

      {/* Idle state hint */}
      {viewState === "idle" && (
        <div className="flex flex-col items-center gap-3 py-12 text-center">
          <div className="w-14 h-14 rounded-full bg-blue-50 flex items-center justify-center">
            <svg
              className="w-7 h-7 text-blue-400"
              fill="none"
              stroke="currentColor"
              strokeWidth="1.5"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z"
              />
            </svg>
          </div>
          <p className="text-sm font-medium text-slate-700">
            Enter your skills above to get started
          </p>
          <p className="text-xs text-slate-400 max-w-xs">
            The AI will match your skills against thousands of ML/AI job
            listings and suggest projects to grow your profile.
          </p>
        </div>
      )}
    </div>
  );
}
