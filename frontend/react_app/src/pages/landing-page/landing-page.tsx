/**
 * LandingPage — redesigned market intelligence hub.
 * Light theme · Inter/Manrope · JD-first flow · Tailwind CSS.
 */
import { useEffect, useRef, useState } from "react";
import { mlApi, type MarketStats, type RoleSkillsItem } from "@/api/client";
import {
  ROLES,
  FLOATING_TAGS,
  UPCOMING_FEATURES,
  type Role,
} from "@/lib/constants";
import { accent, roleColors } from "@/styles/colors";

interface Props {
  onNavigate: (tab: "analyze" | "chat", skills?: string[]) => void;
  /** Called when the user submits a message from the hero chat preview. */
  onChatMessage?: (msg: string) => void;
}

// ── Inline skill demand bar ───────────────────────────────────────────────────

function SkillBar({
  skill,
  pct,
  max,
  rank,
}: {
  skill: string;
  pct: number;
  max: number;
  rank: number;
}) {
  const barWidth = max > 0 ? (pct / max) * 100 : 0;
  const barColors = [
    accent.indigo,
    accent.indigo,
    accent.indigo,
    accent.purple,
    accent.purple,
    accent.purple,
    accent.purple,
    accent.pink,
    accent.pink,
    accent.pink,
  ];
  const color = barColors[rank - 1] ?? "#94a3b8";
  return (
    <div className="flex items-center gap-2.5 py-[5px]">
      <div
        className="w-[100px] shrink-0 text-right text-xs font-medium text-slate-500 overflow-hidden text-ellipsis whitespace-nowrap"
        title={skill}
      >
        {skill}
      </div>
      <div className="flex-1 h-1.5 bg-slate-200 rounded-full overflow-hidden">
        <div
          className="h-full rounded-full transition-[width] duration-700 ease-out"
          style={{ width: `${barWidth}%`, background: color }}
        />
      </div>
      <div className="w-9 text-right text-[11px] font-bold" style={{ color }}>
        {(pct * 100).toFixed(0)}%
      </div>
    </div>
  );
}

// ── Main component ────────────────────────────────────────────────────────────

export default function LandingPage({ onNavigate, onChatMessage }: Props) {
  const [stats, setStats] = useState<MarketStats | null>(null);
  const [loadingStats, setLoadingStats] = useState(true);
  const [roleSkillsData, setRoleSkillsData] = useState<RoleSkillsItem[]>([]);
  const [heroTab, setHeroTab] = useState<"jd" | "chat">("jd");
  const [activeRole, setActiveRole] = useState<Role>(ROLES[0]);
  const [chatInput, setChatInput] = useState("");

  // JD flow state
  const [jdText, setJdText] = useState("");
  const [extracting, setExtracting] = useState(false);
  const [extractError, setExtractError] = useState("");
  const [extractedSkills, setExtractedSkills] = useState<string[] | null>(null);

  const heroRef = useRef<HTMLElement>(null);

  useEffect(() => {
    mlApi
      .marketStats(10)
      .then(setStats)
      .catch(() => null)
      .finally(() => setLoadingStats(false));
    mlApi
      .skillsByRole(10)
      .then(setRoleSkillsData)
      .catch(() => null);
  }, []);

  const handleCheckFit = async () => {
    if (!jdText.trim() || extracting) return;
    setExtracting(true);
    setExtractError("");
    setExtractedSkills(null);
    try {
      const res = await mlApi.extractJD(jdText.trim());
      setExtractedSkills(res.skills);
    } catch {
      setExtractError(
        "Could not extract skills — make sure the API is running.",
      );
    } finally {
      setExtracting(false);
    }
  };

  const totalJobs = stats?.total_jobs ?? 0;
  const topSkills = stats?.top_skills ?? [];
  const maxPct = topSkills.length > 0 ? topSkills[0].pct_of_jobs : 1;

  return (
    <div className="font-[Inter,system-ui,sans-serif] bg-slate-50 text-slate-900 min-h-screen">
      <style>{`
        @keyframes floatTag {
          from { transform: translateY(0px) rotate(-1deg); opacity: 0.6; }
          to   { transform: translateY(-12px) rotate(1deg); opacity: 1; }
        }
        @keyframes pulse {
          0%, 100% { opacity: 1; } 50% { opacity: 0.4; }
        }
        * { box-sizing: border-box; }
        body { margin: 0; }
        a { text-decoration: none; }
        @media (max-width: 768px) {
          .lp-nav-links { display: none !important; }
          .lp-footer-cols { flex-direction: column; gap: 6px; align-items: center; text-align: center; }
        }
      `}</style>

      {/* ── Navbar ──────────────────────────────────────────────────────── */}
      <nav className="sticky top-0 z-50 flex items-center justify-between px-8 h-[60px] bg-slate-50/90 backdrop-blur-md border-b border-slate-200">
        <div className="text-lg font-extrabold text-slate-900 tracking-tight [font-family:'Manrope',system-ui,sans-serif]">
          <span className="text-indigo-500">Job</span>Pulse
          <span className="text-pink-500">.</span>AI
        </div>
      </nav>

      {/* ── Hero ────────────────────────────────────────────────────────── */}
      <section
        ref={heroRef}
        className="relative overflow-visible px-5 py-12 md:px-8 md:py-[72px] bg-gradient-to-br from-[#f0f4ff] via-[#faf5ff] to-[#fff7f0]"
      >
        {FLOATING_TAGS.map((tag, i) => {
          const colors = [
            accent.indigo,
            accent.purple,
            accent.pink,
            accent.emerald,
            accent.amber,
          ];
          const col = i % 5;
          const row = Math.floor(i / 5);
          const color = colors[col];
          return (
            <span
              key={tag}
              className="absolute rounded-full px-3 py-[5px] text-xs font-semibold pointer-events-none"
              style={{
                left: `${8 + col * 20 + (row % 2) * 10}%`,
                top: `${10 + row * 22}%`,
                background: `${color}0d`,
                border: `1px solid ${color}25`,
                color,
                animation: `floatTag ${3 + (i % 4)}s ease-in-out ${i * 0.3}s infinite alternate`,
              }}
            >
              {tag}
            </span>
          );
        })}

        <div className="max-w-[1100px] mx-auto grid grid-cols-1 md:grid-cols-2 gap-8 md:gap-12 items-center">
          {/* Left column */}
          <div className="relative z-10">
            <div className="inline-flex items-center gap-1.5 bg-indigo-500/[0.08] border border-indigo-500/20 text-indigo-500 rounded-full px-3 py-1 text-xs font-semibold mb-4">
              <span
                className="w-1.5 h-1.5 rounded-full bg-emerald-500 inline-block"
                style={{
                  animation: "floatTag 2s ease-in-out infinite alternate",
                }}
              />
              Live · {totalJobs.toLocaleString() || "10,000+"} jobs indexed
            </div>
            <h1 className="[font-family:'Manrope',system-ui,sans-serif] font-extrabold text-[clamp(2rem,4vw,2.75rem)] leading-[1.15] text-slate-900 mb-4 tracking-[-1px]">
              Are you a good fit
              <br />
              <span className="bg-gradient-to-br from-indigo-500 to-pink-500 bg-clip-text text-transparent">
                for this role?
              </span>
            </h1>
            <p className="text-[15px] text-slate-500 leading-[1.7] mb-7 max-w-[420px]">
              Paste a job description and we'll extract the skills, run a FAISS
              vector search across {totalJobs.toLocaleString() || "10,000+"}{" "}
              real postings, and surface your exact gaps.
            </p>
            <div className="flex gap-6">
              {[
                {
                  val: totalJobs
                    ? `${(totalJobs / 1000).toFixed(0)}k+`
                    : "10k+",
                  label: "Jobs",
                },
                {
                  val: stats?.total_skills ? `${stats.total_skills}+` : "600+",
                  label: "Skills tracked",
                },
                { val: topSkills[0]?.skill ?? "Python", label: "Top skill" },
              ].map(({ val, label }) => (
                <div key={label} className="flex flex-col gap-0.5">
                  <span className="[font-family:'Manrope',system-ui,sans-serif] font-extrabold text-[22px] text-slate-900">
                    {val}
                  </span>
                  <span className="text-[11px] font-medium text-slate-400 tracking-[0.5px] uppercase">
                    {label}
                  </span>
                </div>
              ))}
            </div>
          </div>

          {/* Right column — hero card */}
          <div className="relative z-10">
            <div className="bg-white rounded-[20px] border border-slate-200 shadow-[0_20px_60px_rgba(0,0,0,0.08),0_4px_16px_rgba(99,102,241,0.06)] overflow-hidden">
              {/* Tabs */}
              <div className="flex border-b border-slate-200">
                <button
                  className={`flex-1 py-3.5 text-[13px] font-semibold border-0 cursor-pointer transition-all duration-200 border-b-2 ${heroTab === "jd" ? "bg-white text-indigo-500 border-b-indigo-500" : "bg-slate-50 text-slate-400 border-b-transparent"}`}
                  onClick={() => setHeroTab("jd")}
                >
                  📋 Check Job Fit
                </button>
                <button
                  className={`flex-1 py-3.5 text-[13px] font-semibold border-0 cursor-pointer transition-all duration-200 border-b-2 ${heroTab === "chat" ? "bg-white text-indigo-500 border-b-indigo-500" : "bg-slate-50 text-slate-400 border-b-transparent"}`}
                  onClick={() => setHeroTab("chat")}
                >
                  💬 Ask AI Advisor
                </button>
              </div>

              {heroTab === "jd" ? (
                <div className="p-5 flex flex-col gap-3">
                  <textarea
                    value={jdText}
                    onChange={(e) => {
                      setJdText(e.target.value);
                      setExtractedSkills(null);
                      setExtractError("");
                    }}
                    placeholder={
                      'Paste a job description here…\ne.g. "We are looking for a Senior ML Engineer with experience in PyTorch, AWS SageMaker…"'
                    }
                    rows={5}
                    className="w-full border border-slate-200 rounded-[10px] px-3.5 py-3 text-[13px] leading-[1.6] text-slate-900 resize-none outline-none bg-slate-50 transition-colors duration-200 focus:border-indigo-500 [font-family:'DM_Sans',sans-serif]"
                  />

                  {extractedSkills && extractedSkills.length > 0 && (
                    <div className="flex flex-col gap-2">
                      <p className="text-xs text-indigo-500 font-semibold m-0">
                        {extractedSkills.length} skills extracted:
                      </p>
                      <div className="flex flex-wrap gap-1.5">
                        {extractedSkills.map((s) => (
                          <span
                            key={s}
                            className="inline-flex items-center gap-1 bg-indigo-500/[0.07] border border-indigo-500/[0.15] text-indigo-500 rounded-full px-2.5 py-0.5 text-[11px] font-semibold"
                          >
                            {s}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}
                  {extractError && (
                    <p className="text-xs text-red-500 m-0">{extractError}</p>
                  )}

                  {!extractedSkills ? (
                    <button
                      onClick={handleCheckFit}
                      disabled={!jdText.trim() || extracting}
                      className={`rounded-[10px] px-5 py-3 text-[13px] font-bold flex items-center justify-center gap-2 transition-all duration-200 border-0 ${
                        extracting || !jdText.trim()
                          ? "bg-slate-200 text-slate-400 cursor-not-allowed"
                          : "bg-gradient-to-br from-indigo-500 to-purple-500 text-white cursor-pointer"
                      }`}
                    >
                      {extracting ? "Extracting skills…" : "🔍 Check My Fit"}
                    </button>
                  ) : (
                    <button
                      onClick={() => onNavigate("analyze", extractedSkills)}
                      className="bg-gradient-to-br from-indigo-500 to-purple-500 text-white border-0 rounded-[10px] px-5 py-3 text-[13px] font-bold flex items-center justify-center gap-2 cursor-pointer"
                    >
                      ➜ Analyze My Fit
                    </button>
                  )}
                </div>
              ) : (
                <div className="p-5 flex flex-col gap-3">
                  <div className="bg-slate-50 rounded-[10px] p-3.5 flex flex-col gap-2">
                    {[
                      {
                        from: "ai",
                        text: "Hi! I'm your AI career advisor. What role are you targeting?",
                      },
                      {
                        from: "user",
                        text: "I want to become an ML Engineer at a Series B startup.",
                      },
                      {
                        from: "ai",
                        text: "Great! Tell me your current stack — languages, frameworks, tools.",
                      },
                    ].map((msg, i) => (
                      <div
                        key={i}
                        className={`flex ${msg.from === "user" ? "justify-end" : "justify-start"}`}
                      >
                        <div
                          className={`text-xs leading-[1.5] px-3 py-2 max-w-[85%] ${
                            msg.from === "user"
                              ? "bg-gradient-to-br from-indigo-500 to-purple-500 text-white rounded-[12px_12px_2px_12px]"
                              : "bg-white text-slate-900 border border-slate-200 rounded-[12px_12px_12px_2px]"
                          }`}
                        >
                          {msg.text}
                        </div>
                      </div>
                    ))}
                  </div>
                  <div className="flex gap-2">
                    <input
                      value={chatInput}
                      onChange={(e) => setChatInput(e.target.value)}
                      onKeyDown={(e) => {
                        if (e.key === "Enter" && chatInput.trim()) {
                          onChatMessage?.(chatInput.trim());
                          onNavigate("chat");
                          setChatInput("");
                        }
                      }}
                      placeholder="Ask anything about your job fit…"
                      className="flex-1 border border-slate-200 rounded-[10px] px-3.5 py-2.5 text-[13px] outline-none text-slate-900 [font-family:'DM_Sans',sans-serif]"
                    />
                    <button
                      onClick={() => {
                        if (chatInput.trim()) {
                          onChatMessage?.(chatInput.trim());
                          setChatInput("");
                        }
                        onNavigate("chat");
                      }}
                      className="bg-gradient-to-br from-indigo-500 to-purple-500 text-white border-0 rounded-[10px] px-4 py-2.5 text-[13px] font-bold cursor-pointer"
                    >
                      ➜
                    </button>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      </section>

      {/* ── Insight banner ───────────────────────────────────────────────── */}
      <div className="bg-indigo-50 border-t border-b border-indigo-500/15 px-8 py-3.5">
        <div className="max-w-[1100px] mx-auto flex items-center gap-3 flex-wrap">
          <span className="text-lg">💡</span>
          <p className="text-[13px] text-indigo-700 font-medium m-0">
            <strong>Did you know?</strong> {topSkills[0]?.skill ?? "Python"}{" "}
            appears in{" "}
            <strong>
              {topSkills[0]
                ? `${(topSkills[0].pct_of_jobs * 100).toFixed(0)}%`
                : "most"}
            </strong>{" "}
            of all ML job postings — making it the single most valuable skill to
            have on your resume.
          </p>
        </div>
      </div>

      {/* ── Skills demand section ────────────────────────────────────────── */}
      <div className="bg-white border-b border-slate-200">
        <div className="max-w-[1100px] mx-auto px-8 py-16">
          <p className="text-[11px] font-bold tracking-[2px] uppercase text-indigo-500 mb-2">
            Live Market Data
          </p>
          <h2 className="[font-family:'Manrope',system-ui,sans-serif] font-extrabold text-[clamp(1.5rem,3vw,2rem)] text-slate-900 mb-2 tracking-[-0.5px]">
            Most In-Demand Skills
          </h2>
          <p className="text-sm text-slate-500 mb-10">
            % of all job listings that require each skill — derived from{" "}
            {totalJobs.toLocaleString() || "10,000+"} real postings
          </p>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6 md:gap-12 items-start">
            {/* Skill bars */}
            <div className="bg-white rounded-2xl border border-slate-200 shadow-sm p-6 overflow-hidden">
              <div className="border-b border-slate-200 mb-3 pb-3 flex justify-between items-center">
                <span className="text-[13px] font-bold text-slate-900">
                  Top Skills Across All Roles
                </span>
                <span className="text-[11px] font-semibold text-indigo-500 bg-indigo-50 px-2.5 py-0.5 rounded-full">
                  All roles
                </span>
              </div>
              {loadingStats
                ? Array.from({ length: 10 }).map((_, i) => (
                    <div key={i} className="flex items-center gap-2.5 py-1.5">
                      <div
                        className="w-[110px] h-2.5 bg-slate-100 rounded"
                        style={{
                          animation:
                            "floatTag 1.5s ease-in-out infinite alternate",
                        }}
                      />
                      <div
                        className="flex-1 h-1.5 bg-slate-100 rounded-full"
                        style={{
                          animation:
                            "floatTag 1.5s ease-in-out infinite alternate",
                        }}
                      />
                      <div className="w-7 h-2.5 bg-slate-100 rounded" />
                    </div>
                  ))
                : topSkills.map((s, i) => (
                    <SkillBar
                      key={s.skill}
                      skill={s.skill}
                      pct={s.pct_of_jobs}
                      max={maxPct}
                      rank={i + 1}
                    />
                  ))}
            </div>

            {/* Stats + CTA */}
            <div className="flex flex-col gap-4">
              <div className="grid grid-cols-2 gap-3">
                {[
                  {
                    val: totalJobs
                      ? `${(totalJobs / 1000).toFixed(0)}k+`
                      : "10k+",
                    label: "Jobs analyzed",
                    color: "#6366f1",
                    bg: "#eef2ff",
                  },
                  {
                    val: stats?.total_skills
                      ? `${stats.total_skills}+`
                      : "600+",
                    label: "Skills tracked",
                    color: "#10b981",
                    bg: "#ecfdf5",
                  },
                  {
                    val: Object.keys(stats?.roles ?? {}).length || 5,
                    label: "Roles covered",
                    color: "#f97316",
                    bg: "#fff7ed",
                  },
                  {
                    val: topSkills[0]
                      ? `${(topSkills[0].pct_of_jobs * 100).toFixed(0)}%`
                      : "—",
                    label: `Jobs need ${topSkills[0]?.skill ?? "Python"}`,
                    color: "#8b5cf6",
                    bg: "#f5f3ff",
                  },
                ].map(({ val, label, color, bg }) => (
                  <div
                    key={label}
                    className="rounded-xl p-4"
                    style={{ background: bg }}
                  >
                    <div
                      className="[font-family:'Manrope',system-ui,sans-serif] font-extrabold text-2xl mb-1"
                      style={{ color }}
                    >
                      {val}
                    </div>
                    <div className="text-[11px] font-medium text-slate-500">
                      {label}
                    </div>
                  </div>
                ))}
              </div>

              <div className="bg-gradient-to-br from-indigo-50 to-purple-50 border border-indigo-500/15 rounded-2xl p-5">
                <h3 className="[font-family:'Manrope',system-ui,sans-serif] font-extrabold text-base text-slate-900 mb-2">
                  What's your gap?
                </h3>
                <p className="text-[13px] text-slate-500 mb-4 leading-[1.6]">
                  Paste a JD, enter your skills, or chat — the AI will pinpoint
                  exactly what's missing.
                </p>
                <div className="flex gap-2.5">
                  <button
                    onClick={() => {
                      heroRef.current?.scrollIntoView({ behavior: "smooth" });
                      setHeroTab("jd");
                    }}
                    className="flex-1 bg-gradient-to-br from-indigo-500 to-purple-500 text-white border-0 rounded-[10px] py-2.5 text-[13px] font-bold cursor-pointer"
                  >
                    Check Job Fit
                  </button>
                  <button
                    onClick={() => onNavigate("chat")}
                    className="flex-1 bg-white border border-slate-200 rounded-[10px] py-2.5 text-[13px] font-bold text-indigo-500 cursor-pointer"
                  >
                    Chat with AI
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* ── Skills by role ───────────────────────────────────────────────── */}
      <div className="bg-slate-50 border-b border-slate-200">
        <div className="max-w-[1100px] mx-auto px-8 py-16">
          <p className="text-[11px] font-bold tracking-[2px] uppercase text-indigo-500 mb-2">
            Role Intelligence
          </p>
          <h2 className="[font-family:'Manrope',system-ui,sans-serif] font-extrabold text-[clamp(1.5rem,3vw,2rem)] text-slate-900 mb-2 tracking-[-0.5px]">
            Skills by Role
          </h2>
          <p className="text-sm text-slate-500 mb-10">
            Top skills required for each job category — click a role to explore
          </p>

          {/* Role filter pills */}
          <div className="flex gap-2 flex-wrap mb-6">
            {ROLES.map((r) => (
              <button
                key={r}
                onClick={() => setActiveRole(r)}
                className="px-3.5 py-1.5 rounded-full text-xs font-semibold cursor-pointer transition-all duration-200 border"
                style={
                  activeRole === r
                    ? {
                        borderColor: roleColors[r],
                        background: `${roleColors[r]}14`,
                        color: roleColors[r],
                      }
                    : {
                        borderColor: "#e2e8f0",
                        background: "#fff",
                        color: "#64748b",
                      }
                }
              >
                {r}
              </button>
            ))}
          </div>

          {/* Per-role skill bars */}
          {(() => {
            const roleData = roleSkillsData.find(
              (rd) => rd.role === activeRole,
            );
            const skills = roleData?.skills ?? [];
            const maxScore = skills[0]?.pct_of_jobs ?? 1;
            if (roleSkillsData.length === 0) {
              return (
                <div className="bg-white rounded-2xl border border-slate-200 shadow-sm p-6">
                  <p className="text-[13px] text-slate-400 text-center py-6 m-0">
                    Loading role data…
                  </p>
                </div>
              );
            }
            if (skills.length === 0) {
              return (
                <div className="bg-white rounded-2xl border border-slate-200 shadow-sm p-6">
                  <p className="text-[13px] text-slate-400 text-center py-6 m-0">
                    No data for {activeRole}
                  </p>
                </div>
              );
            }
            return (
              <div className="bg-white rounded-2xl border border-slate-200 shadow-sm p-6">
                <div className="flex items-center justify-between mb-3 pb-2.5 border-b border-slate-200">
                  <span className="text-[13px] font-bold text-slate-900">
                    Top skills for {activeRole}
                  </span>
                  <span
                    className="text-[11px] font-bold px-2.5 py-0.5 rounded-full"
                    style={{
                      background: `${roleColors[activeRole]}14`,
                      color: roleColors[activeRole],
                    }}
                  >
                    {skills.length} skills
                  </span>
                </div>
                {skills.map((s, i) => (
                  <SkillBar
                    key={s.skill}
                    skill={s.skill}
                    pct={s.pct_of_jobs}
                    max={maxScore}
                    rank={i + 1}
                  />
                ))}
              </div>
            );
          })()}
        </div>
      </div>

      {/* ── Upcoming features ────────────────────────────────────────────── */}
      <div className="bg-white border-b border-slate-200">
        <div className="max-w-[1100px] mx-auto px-8 py-16">
          <p className="text-[11px] font-bold tracking-[2px] uppercase text-indigo-500 mb-2">
            Coming Soon
          </p>
          <h2 className="[font-family:'Manrope',system-ui,sans-serif] font-extrabold text-[clamp(1.5rem,3vw,2rem)] text-slate-900 mb-2 tracking-[-0.5px]">
            More features on the way
          </h2>
          <p className="text-sm text-slate-500 mb-10">
            We're building the most complete ML career intelligence platform —
            here's what's next.
          </p>

          <div className="grid grid-cols-[repeat(auto-fill,minmax(240px,1fr))] gap-4">
            {UPCOMING_FEATURES.map(
              ({ icon, title, desc, color, bg, border }) => (
                <div
                  key={title}
                  className="rounded-2xl p-6"
                  style={{ background: bg, border: `1px solid ${border}` }}
                >
                  <div className="text-[28px] mb-3">{icon}</div>
                  <h3 className="[font-family:'Manrope',system-ui,sans-serif] font-extrabold text-[15px] text-slate-900 mb-2">
                    {title}
                  </h3>
                  <p className="text-[13px] text-slate-500 leading-[1.6] mb-3.5">
                    {desc}
                  </p>
                  <span
                    className="inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-[11px] font-semibold"
                    style={{
                      background: `${color}12`,
                      border: `1px solid ${color}25`,
                      color,
                    }}
                  >
                    Coming soon
                  </span>
                </div>
              ),
            )}
          </div>
        </div>
      </div>

      {/* ── How it works ─────────────────────────────────────────────────── */}
      <div className="bg-slate-50 border-b border-slate-200">
        <div className="max-w-[1100px] mx-auto px-8 py-16">
          <p className="text-[11px] font-bold tracking-[2px] uppercase text-indigo-500 mb-2">
            How It Works
          </p>
          <h2 className="[font-family:'Manrope',system-ui,sans-serif] font-extrabold text-[clamp(1.5rem,3vw,2rem)] text-slate-900 mb-2 tracking-[-0.5px]">
            Three steps to clarity
          </h2>
          <p className="text-sm text-slate-500 mb-10">
            From job description to personalized project roadmap in seconds.
          </p>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {[
              {
                step: "01",
                icon: "📋",
                title: "Paste a job description",
                detail:
                  "Drop any JD — we extract the required skills automatically via JobBERT NER. No manual input needed.",
              },
              {
                step: "02",
                icon: "🔍",
                title: "Semantic matching",
                detail:
                  "Your skills are embedded and compared against 10k+ real postings using FAISS vector search. Matches in milliseconds.",
              },
              {
                step: "03",
                icon: "🎯",
                title: "AI project roadmap",
                detail:
                  "An LLM generates portfolio projects targeting your exact skill gaps. Each completable in ≤40 hours.",
              },
            ].map(({ step, icon, title, detail }) => (
              <div
                key={step}
                className="bg-white rounded-2xl border border-slate-200 shadow-sm p-6 relative overflow-visible"
              >
                <div className="absolute -top-3.5 left-5 bg-gradient-to-br from-indigo-500 to-purple-500 text-white rounded-lg px-2.5 py-0.5 text-[11px] font-extrabold tracking-[1px] [font-family:'Manrope',system-ui,sans-serif]">
                  STEP {step}
                </div>
                <div className="text-[28px] mb-3 mt-2">{icon}</div>
                <h3 className="[font-family:'Manrope',system-ui,sans-serif] font-extrabold text-[15px] text-slate-900 mb-2">
                  {title}
                </h3>
                <p className="text-[13px] text-slate-500 leading-[1.6] m-0">
                  {detail}
                </p>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* ── Bottom CTA ───────────────────────────────────────────────────── */}
      <div className="bg-gradient-to-br from-indigo-500 via-purple-500 to-pink-500 px-8 py-16 text-center">
        <h2 className="[font-family:'Manrope',system-ui,sans-serif] font-extrabold text-[clamp(1.75rem,3vw,2.5rem)] text-white mb-4 tracking-[-0.5px]">
          Ready to close your skill gaps?
        </h2>
        <p className="text-[15px] text-white/80 mb-8 max-w-[480px] mx-auto">
          Paste a job description or tell the AI your background — we'll do the
          rest.
        </p>
        <div className="flex gap-3 justify-center flex-wrap">
          <button
            onClick={() => {
              heroRef.current?.scrollIntoView({ behavior: "smooth" });
              setHeroTab("jd");
            }}
            className="bg-white text-indigo-500 border-0 rounded-xl px-7 py-3.5 text-sm font-bold cursor-pointer"
          >
            Check Job Fit
          </button>
          <button
            onClick={() => onNavigate("chat")}
            className="bg-white/15 text-white border border-white/30 rounded-xl px-7 py-3.5 text-sm font-bold cursor-pointer"
          >
            Chat with AI Advisor
          </button>
        </div>
      </div>

      {/* ── Footer ───────────────────────────────────────────────────────── */}
      <footer className="bg-slate-900 text-slate-400 px-8 py-6 flex justify-between items-center flex-wrap gap-3 lp-footer-cols">
        <span className="[font-family:'Manrope',system-ui,sans-serif] font-extrabold text-base text-white">
          <span className="text-indigo-500">Job</span>Pulse
          <span className="text-pink-500">.</span>AI
        </span>
        <span className="text-xs">
          Built with FAISS · sentence-transformers · Gemini 2.0 Flash ·
          LangGraph
        </span>
        <span className="text-xs">
          10k+ real postings · NLP-powered · open-source
        </span>
      </footer>
    </div>
  );
}
