/**
 * ChatInterface — message thread UI for the FR-08 RAG chatbot.
 * Renders tool call badges per message to show when the agent used FAISS / gap tools.
 */
import React, { useState, useRef, useEffect, FormEvent } from "react";
import { mlApi, type ChatResponse } from "@/api/client";
import { brand } from "@/styles/colors";

interface Message {
  role: "user" | "assistant";
  content: string;
  toolCalls?: string[];
}

interface Props {
  userSkills?: string[];
  /** Extra Tailwind classes for the root wrapper — use to override the default height. */
  className?: string;
  /** If set, auto-sends this message when the component mounts (or when it changes). */
  initialMessage?: string;
  /** Called after the initial message has been sent so the parent can clear it. */
  onMessageConsumed?: () => void;
}

const BOT_ICON = (
  <span className="flex items-center justify-center w-7 h-7 rounded-full bg-blue-600 text-white text-xs shrink-0 font-bold">
    AI
  </span>
);

export default function ChatInterface({
  userSkills,
  className = "h-[620px]",
  initialMessage,
  onMessageConsumed,
}: Props) {
  const [messages, setMessages] = useState<Message[]>([
    {
      role: "assistant",
      content:
        "Hi! I'm your AI career assistant. Ask me about ML job skills, what roles suit your background, or how to close skill gaps.",
    },
  ]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [sessionId, setSessionId] = useState<string | undefined>();
  const bottomRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  // Auto-send initialMessage (e.g. from hero card) when it changes to a non-empty value
  useEffect(() => {
    if (!initialMessage?.trim()) return;
    const text = initialMessage.trim();
    onMessageConsumed?.(); // clear in parent immediately so it won't re-fire
    const timer = setTimeout(async () => {
      setMessages((prev) => [...prev, { role: "user", content: text }]);
      setLoading(true);
      try {
        const resp: ChatResponse = await mlApi.chat({
          message: text,
          user_skills: userSkills,
        });
        setSessionId(resp.session_id);
        setMessages((prev) => [
          ...prev,
          {
            role: "assistant",
            content: resp.answer,
            toolCalls: resp.tool_calls_made,
          },
        ]);
      } catch {
        setMessages((prev) => [
          ...prev,
          {
            role: "assistant",
            content: "Sorry, something went wrong. Please try again.",
          },
        ]);
      } finally {
        setLoading(false);
      }
    }, 350);
    return () => clearTimeout(timer);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [initialMessage]);

  const sendMessage = async (e: FormEvent) => {
    e.preventDefault();
    const text = input.trim();
    if (!text || loading) return;

    setMessages((prev) => [...prev, { role: "user", content: text }]);
    setInput("");
    setLoading(true);

    try {
      const resp: ChatResponse = await mlApi.chat({
        message: text,
        session_id: sessionId,
        user_skills: userSkills,
      });
      setSessionId(resp.session_id);
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: resp.answer,
          toolCalls: resp.tool_calls_made,
        },
      ]);
    } catch {
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: "Sorry, something went wrong. Please try again.",
        },
      ]);
    } finally {
      setLoading(false);
      setTimeout(() => inputRef.current?.focus(), 50);
    }
  };

  return (
    <div
      className={`flex flex-col rounded-xl border border-slate-200 bg-white shadow-sm overflow-hidden ${className}`}
    >
      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-4 py-5 space-y-5">
        {messages.map((msg, i) => (
          <div
            key={i}
            className={`flex gap-3 ${msg.role === "user" ? "justify-end" : "justify-start"}`}
          >
            {msg.role === "assistant" && BOT_ICON}

            <div
              className={`max-w-[78%] ${msg.role === "user" ? "items-end" : "items-start"} flex flex-col gap-1`}
            >
              <div
                className={`rounded-2xl px-4 py-3 text-sm leading-relaxed ${
                  msg.role === "user"
                    ? "bg-blue-600 text-white rounded-br-sm"
                    : "bg-slate-100 text-slate-800 rounded-bl-sm"
                }`}
              >
                <p className="whitespace-pre-wrap">{msg.content}</p>
              </div>

              {/* Tool call badges */}
              {msg.toolCalls && msg.toolCalls.length > 0 && (
                <div className="flex flex-wrap gap-1 px-1">
                  {msg.toolCalls.map((tool, ti) => (
                    <span
                      key={ti}
                      className="inline-flex items-center gap-0.5 rounded-full bg-violet-50 px-2 py-0.5 text-[10px] font-mono font-medium text-violet-600 ring-1 ring-violet-100"
                    >
                      <svg
                        className="w-2.5 h-2.5"
                        fill="currentColor"
                        viewBox="0 0 20 20"
                      >
                        <path
                          fillRule="evenodd"
                          d="M11.3 1.046A1 1 0 0112 2v5h4a1 1 0 01.82 1.573l-7 10A1 1 0 018 18v-5H4a1 1 0 01-.82-1.573l7-10a1 1 0 011.12-.38z"
                          clipRule="evenodd"
                        />
                      </svg>
                      {tool}
                    </span>
                  ))}
                </div>
              )}
            </div>
          </div>
        ))}

        {/* Typing indicator */}
        {loading && (
          <div className="flex gap-3 justify-start">
            {BOT_ICON}
            <div className="bg-slate-100 rounded-2xl rounded-bl-sm px-4 py-3">
              <span className="inline-flex gap-1 items-center">
                {[0, 150, 300].map((delay, i) => (
                  <span
                    key={i}
                    className="w-1.5 h-1.5 rounded-full bg-slate-400 animate-bounce"
                    style={{ animationDelay: `${delay}ms` }}
                  />
                ))}
              </span>
            </div>
          </div>
        )}

        <div ref={bottomRef} />
      </div>

      {/* Input bar */}
      <form
        onSubmit={sendMessage}
        className="border-t border-slate-100 p-4 flex gap-2 bg-slate-50/50"
      >
        <input
          ref={inputRef}
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ask about skills, roles, or career gaps…"
          disabled={loading}
          className="flex-1 rounded-lg border border-slate-200 bg-white px-4 py-2.5 text-sm shadow-sm
                     focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent
                     disabled:opacity-50 placeholder:text-slate-400 transition"
        />
        <button
          type="submit"
          disabled={!input.trim() || loading}
          className="rounded-lg bg-blue-600 px-5 py-2.5 text-sm font-semibold text-white shadow-sm
                     hover:bg-blue-700 disabled:opacity-40 disabled:cursor-not-allowed transition-colors
                     flex items-center gap-1.5"
        >
          <svg
            className="w-4 h-4"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8"
            />
          </svg>
          Send
        </button>
      </form>
    </div>
  );
}
