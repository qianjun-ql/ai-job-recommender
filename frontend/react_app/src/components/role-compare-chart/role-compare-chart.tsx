/**
 * RoleCompareChart — grouped horizontal bar chart showing top skill demand by role.
 * Answers: "Which skills matter most for each role?"
 * Data from GET /api/ml/skills_by_role/
 */
import React, { useEffect, useState } from "react";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  Legend,
  ResponsiveContainer,
  CartesianGrid,
} from "recharts";
import { mlApi, type RoleSkillsItem } from "@/api/client";

// Color per role (consistent with brand palette)
const ROLE_COLORS: Record<string, string> = {
  "ML Engineer": "#2563eb",
  "Data Scientist": "#10b981",
  "AI Engineer": "#8b5cf6",
  "Data Engineer": "#f59e0b",
  SWE: "#f43f5e",
};

// Short labels for the axis
const ROLE_SHORT: Record<string, string> = {
  "ML Engineer": "ML Eng",
  "Data Scientist": "Data Sci",
  "AI Engineer": "AI Eng",
  "Data Engineer": "Data Eng",
  SWE: "SWE",
};

interface ChartRow {
  skill: string;
  [role: string]: string | number;
}

function pivotData(
  roleItems: RoleSkillsItem[],
  topN: number,
): { rows: ChartRow[]; roles: string[] } {
  // Collect top skills by picking up to topN from each role, then taking union
  const skillSet = new Set<string>();
  roleItems.forEach((ri) =>
    ri.skills.slice(0, topN).forEach((s) => skillSet.add(s.skill)),
  );

  // Score each skill by sum of pct_of_jobs across roles (for consistent ordering)
  const skillScore: Record<string, number> = {};
  for (const sk of skillSet) {
    skillScore[sk] = roleItems.reduce((sum, ri) => {
      const match = ri.skills.find((s) => s.skill === sk);
      return sum + (match ? match.pct_of_jobs : 0);
    }, 0);
  }

  // Sort skills by score desc, take top topN overall
  const orderedSkills = [...skillSet]
    .sort((a, b) => skillScore[b] - skillScore[a])
    .slice(0, topN);

  const roles = roleItems.map((ri) => ri.role);

  const rows: ChartRow[] = orderedSkills.map((skill) => {
    const row: ChartRow = { skill };
    for (const ri of roleItems) {
      const match = ri.skills.find((s) => s.skill === skill);
      row[ri.role] = match ? Math.round(match.pct_of_jobs * 100) : 0;
    }
    return row;
  });

  return { rows: rows.reverse(), roles }; // reverse so highest at top in horizontal chart
}

interface TooltipProps {
  active?: boolean;
  payload?: Array<{ name: string; value: number; color: string }>;
  label?: string;
}

function CustomTooltip({ active, payload, label }: TooltipProps) {
  if (!active || !payload?.length) return null;
  return (
    <div className="rounded-lg border border-slate-200 bg-white px-3 py-2.5 shadow-lg text-xs min-w-[160px]">
      <p className="font-semibold text-slate-900 mb-1.5">{label}</p>
      {payload.map((p) => (
        <div
          key={p.name}
          className="flex items-center justify-between gap-4 py-0.5"
        >
          <span className="flex items-center gap-1.5 text-slate-600">
            <span
              className="w-2 h-2 rounded-full shrink-0"
              style={{ background: p.color }}
            />
            {ROLE_SHORT[p.name] ?? p.name}
          </span>
          <span
            className="font-semibold tabular-nums"
            style={{ color: p.color }}
          >
            {p.value}%
          </span>
        </div>
      ))}
    </div>
  );
}

interface Props {
  topN?: number;
}

export default function RoleCompareChart({ topN = 8 }: Props) {
  const [rows, setRows] = useState<ChartRow[]>([]);
  const [roles, setRoles] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setLoading(true);
    mlApi
      .skillsByRole(topN)
      .then((roleItems) => {
        const { rows: r, roles: ro } = pivotData(roleItems, topN);
        setRows(r);
        setRoles(ro);
      })
      .catch(() =>
        setError("Failed to load role data. Make sure the API is running."),
      )
      .finally(() => setLoading(false));
  }, [topN]);

  if (loading) {
    return (
      <div className="rounded-xl border border-slate-200 bg-white p-10 flex flex-col items-center justify-center gap-3">
        <div className="w-8 h-8 rounded-full border-2 border-blue-200 border-t-blue-600 animate-spin" />
        <p className="text-sm text-slate-400">Loading role comparison…</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="rounded-xl border border-rose-200 bg-rose-50 p-8 text-center">
        <p className="text-sm text-rose-600 font-medium">{error}</p>
      </div>
    );
  }

  return (
    <div className="rounded-xl border border-slate-200 bg-white shadow-sm overflow-hidden">
      <div className="px-6 py-4 border-b border-slate-100 flex items-center justify-between">
        <div>
          <h2 className="font-semibold text-slate-900">Skills by Role</h2>
          <p className="text-xs text-slate-400 mt-0.5">
            % of job listings requiring each skill
          </p>
        </div>
        <div className="flex gap-2 flex-wrap justify-end">
          {roles.map((r) => (
            <span
              key={r}
              className="inline-flex items-center gap-1.5 text-[11px] font-medium text-slate-600"
            >
              <span
                className="w-2 h-2 rounded-full"
                style={{ background: ROLE_COLORS[r] ?? "#94a3b8" }}
              />
              {ROLE_SHORT[r] ?? r}
            </span>
          ))}
        </div>
      </div>

      <div className="p-6">
        <ResponsiveContainer width="100%" height={rows.length * 40 + 40}>
          <BarChart
            data={rows}
            layout="vertical"
            barSize={10}
            barGap={2}
            barCategoryGap={8}
          >
            <CartesianGrid horizontal={false} stroke="#f1f5f9" />
            <XAxis
              type="number"
              domain={[0, 100]}
              tickFormatter={(v) => `${v}%`}
              tick={{ fontSize: 11, fill: "#94a3b8" }}
              tickLine={false}
              axisLine={{ stroke: "#f1f5f9" }}
            />
            <YAxis
              type="category"
              dataKey="skill"
              width={110}
              tick={{ fontSize: 11, fill: "#475569" }}
              tickLine={false}
              axisLine={false}
            />
            <Tooltip content={<CustomTooltip />} cursor={{ fill: "#f8fafc" }} />
            {roles.map((r) => (
              <Bar
                key={r}
                dataKey={r}
                fill={ROLE_COLORS[r] ?? "#94a3b8"}
                radius={[0, 3, 3, 0]}
              />
            ))}
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
