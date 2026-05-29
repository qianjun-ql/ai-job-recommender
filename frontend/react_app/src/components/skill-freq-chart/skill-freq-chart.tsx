/**
 * SkillFreqChart — horizontal bar chart of most-demanded skills across all jobs.
 * Data from GET /api/ml/top_skills/
 */
import React, { useEffect, useState } from "react";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from "recharts";
import { mlApi, type SkillDemand } from "@/api/client";
import { chart } from "@/styles/colors";

interface TooltipPayload {
  payload: SkillDemand;
}

interface CustomTooltipProps {
  active?: boolean;
  payload?: TooltipPayload[];
}

function CustomTooltip({ active, payload }: CustomTooltipProps) {
  if (!active || !payload?.length) return null;
  const d = payload[0].payload;
  return (
    <div className="rounded-lg border border-slate-200 bg-white px-3 py-2 shadow-lg text-xs">
      <p className="font-semibold text-slate-900 mb-0.5">{d.skill}</p>
      <p className="text-slate-500">
        {d.demand_count.toLocaleString()} job listings
      </p>
      <p className="text-blue-600 font-medium">
        {d.pct_of_jobs.toFixed(1)}% of all jobs
      </p>
    </div>
  );
}

interface Props {
  n?: number;
}

export default function SkillFreqChart({ n = 20 }: Props) {
  const [data, setData] = useState<SkillDemand[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setLoading(true);
    mlApi
      .marketStats(n)
      .then((r) => setData(r.top_skills))
      .catch(() =>
        setError("Failed to load skill data. Make sure the API is running."),
      )
      .finally(() => setLoading(false));
  }, [n]);

  if (loading) {
    return (
      <div className="rounded-xl border border-slate-200 bg-white p-10 flex flex-col items-center justify-center gap-3">
        <div className="w-8 h-8 rounded-full border-2 border-blue-200 border-t-blue-600 animate-spin" />
        <p className="text-sm text-slate-400">Loading skill demand data…</p>
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

  const chartData = [...data].reverse();

  return (
    <div className="rounded-xl border border-slate-200 bg-white shadow-sm overflow-hidden">
      <div className="px-6 py-4 border-b border-slate-100 flex items-center justify-between">
        <div>
          <h2 className="font-semibold text-slate-900">
            Top {n} In-Demand Skills
          </h2>
          <p className="text-xs text-slate-400 mt-0.5">
            Based on ML/AI job listings in dataset
          </p>
        </div>
        <span className="rounded-full bg-blue-50 px-3 py-1 text-xs font-semibold text-blue-700">
          {data.length} skills
        </span>
      </div>

      <div className="p-6">
        <ResponsiveContainer width="100%" height={n * 30}>
          <BarChart
            data={chartData}
            layout="vertical"
            barSize={16}
            margin={{ left: 8, right: 24 }}
          >
            <XAxis
              type="number"
              tick={{ fontSize: 11, fill: "#94a3b8" }}
              tickLine={false}
              axisLine={{ stroke: "#f1f5f9" }}
            />
            <YAxis
              type="category"
              dataKey="skill"
              width={140}
              tick={{ fontSize: 11, fill: "#475569" }}
              tickLine={false}
              axisLine={false}
            />
            <Tooltip content={<CustomTooltip />} cursor={{ fill: "#f8fafc" }} />
            <Bar
              dataKey="demand_count"
              name="Job listings"
              radius={[0, 4, 4, 0]}
            >
              {chartData.map((_, i) => (
                <Cell key={i} fill={chart.bars[i % chart.bars.length]} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
