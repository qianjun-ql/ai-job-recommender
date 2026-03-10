/**
 * SkillInput — tag chip input for entering user skills + optional role select.
 * Press Enter or comma to add a skill. Click × to remove.
 */
import React, { useState, KeyboardEvent } from "react";
import { pill } from "@/styles/colors";

const ROLES = [
  "Machine Learning Engineer",
  "Data Scientist",
  "MLOps Engineer",
  "AI Research Engineer",
  "Data Engineer",
  "Computer Vision Engineer",
  "NLP Engineer",
];

interface Props {
  skills: string[];
  role: string;
  onSkillsChange: (skills: string[]) => void;
  onRoleChange: (role: string) => void;
}

export default function SkillInput({
  skills,
  role,
  onSkillsChange,
  onRoleChange,
}: Props) {
  const [input, setInput] = useState("");

  const addSkill = (raw: string) => {
    const trimmed = raw.trim().toLowerCase();
    if (trimmed && !skills.includes(trimmed)) {
      onSkillsChange([...skills, trimmed]);
    }
    setInput("");
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter" || e.key === ",") {
      e.preventDefault();
      addSkill(input);
    } else if (e.key === "Backspace" && input === "" && skills.length > 0) {
      onSkillsChange(skills.slice(0, -1));
    }
  };

  const removeSkill = (skill: string) => {
    onSkillsChange(skills.filter((s) => s !== skill));
  };

  return (
    <div className="space-y-5">
      {/* Role selector */}
      <div className="grid sm:grid-cols-2 gap-5">
        <div className="space-y-1.5">
          <label className="block text-xs font-semibold uppercase tracking-widest text-slate-500">
            Target Role
          </label>
          <select
            value={role}
            onChange={(e) => onRoleChange(e.target.value)}
            className="w-full rounded-lg border border-slate-200 bg-white px-3 py-2.5 text-sm text-slate-900 shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition"
          >
            <option value="">Any role</option>
            {ROLES.map((r) => (
              <option key={r} value={r}>
                {r}
              </option>
            ))}
          </select>
        </div>

        <div className="space-y-1.5">
          <label className="block text-xs font-semibold uppercase tracking-widest text-slate-500">
            Skills Added
          </label>
          <div className="flex items-center gap-2 h-10 px-3 rounded-lg border border-slate-200 bg-slate-50 text-sm text-slate-500">
            <span className="text-2xl font-bold text-blue-600 leading-none">
              {skills.length}
            </span>
            <span>
              {skills.length === 1 ? "skill entered" : "skills entered"}
            </span>
          </div>
        </div>
      </div>

      {/* Chip input */}
      <div className="space-y-1.5">
        <label className="block text-xs font-semibold uppercase tracking-widest text-slate-500">
          Your Skills
        </label>
        <div
          className="min-h-[56px] flex flex-wrap gap-1.5 rounded-lg border border-slate-200 bg-white px-3 py-2.5 shadow-sm
                     focus-within:ring-2 focus-within:ring-blue-500 focus-within:border-transparent transition"
        >
          {skills.map((skill) => (
            <span
              key={skill}
              className={`inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-xs font-medium ${pill.primary}`}
            >
              {skill}
              <button
                type="button"
                onClick={() => removeSkill(skill)}
                className="hover:text-blue-900 focus:outline-none ml-0.5 leading-none"
                aria-label={`Remove ${skill}`}
              >
                ×
              </button>
            </span>
          ))}
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            onBlur={() => input && addSkill(input)}
            placeholder={
              skills.length === 0
                ? "e.g. python, pytorch, mlflow — press Enter to add"
                : ""
            }
            className="flex-1 min-w-[200px] text-sm outline-none bg-transparent text-slate-800 placeholder:text-slate-400"
          />
        </div>
        <p className="text-xs text-slate-400">
          Press{" "}
          <kbd className="rounded bg-slate-100 px-1 py-0.5 font-mono text-[10px]">
            Enter
          </kbd>{" "}
          or{" "}
          <kbd className="rounded bg-slate-100 px-1 py-0.5 font-mono text-[10px]">
            ,
          </kbd>{" "}
          to add · Backspace to remove last
        </p>
      </div>
    </div>
  );
}
