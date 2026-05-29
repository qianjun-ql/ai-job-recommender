/**
 * ChatPage — optional skill context setup + ChatInterface.
 */
import React, { useState } from "react";
import ChatInterface from "@/components/chat-interface/chat-interface";
import SkillInput from "@/components/skill-input/skill-input";
import { pill } from "@/styles/colors";

type Step = "context" | "chat";

export default function ChatPage() {
  const [skills, setSkills] = useState<string[]>([]);
  const [role, setRole] = useState("");
  const [step, setStep] = useState<Step>("context");

  const startChat = () => setStep("chat");

  if (step === "chat") {
    return (
      <div className="space-y-4">
        {/* Context summary bar */}
        <div className="rounded-lg border border-slate-200 bg-white px-4 py-3 flex flex-wrap items-center gap-3">
          <span className="text-xs font-semibold uppercase tracking-widest text-slate-400 shrink-0">
            Context
          </span>
          <div className="flex flex-wrap gap-1.5 flex-1">
            {skills.length > 0 ? (
              skills.map((s) => (
                <span
                  key={s}
                  className={`rounded-full px-2.5 py-0.5 text-[11px] font-medium ${pill.primary}`}
                >
                  {s}
                </span>
              ))
            ) : (
              <span className="text-xs text-slate-400">
                No skill context — answers will be general
              </span>
            )}
          </div>
          <button
            onClick={() => setStep("context")}
            className="text-xs text-blue-600 hover:text-blue-800 font-medium transition-colors shrink-0"
          >
            Edit
          </button>
        </div>

        <ChatInterface userSkills={skills.length > 0 ? skills : undefined} />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
        <div className="mb-6">
          <h2 className="text-lg font-bold text-slate-900">Career Q&A</h2>
          <p className="mt-1 text-sm text-slate-500">
            Optionally add your skills for personalised answers, then start
            chatting with the AI career assistant.
          </p>
        </div>

        <SkillInput
          skills={skills}
          role={role}
          onSkillsChange={setSkills}
          onRoleChange={setRole}
        />

        <div className="mt-6 flex gap-3">
          <button
            onClick={startChat}
            className="flex-1 rounded-lg bg-blue-600 py-3 text-sm font-semibold text-white shadow-sm
                       hover:bg-blue-700 transition-colors flex items-center justify-center gap-2"
          >
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
                d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z"
              />
            </svg>
            {skills.length > 0
              ? `Start Chat with ${skills.length} Skill${skills.length !== 1 ? "s" : ""}`
              : "Start Chat"}
          </button>
        </div>
      </div>
    </div>
  );
}
