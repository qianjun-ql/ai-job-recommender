/**
 * ChatPopup — floating AI Advisor panel anchored to the bottom-right corner.
 * The toggle button is always visible; clicking it opens or closes the panel.
 */
import React, { useEffect, useRef } from "react";
import ChatInterface from "@/components/chat-interface/chat-interface";

interface Props {
  open: boolean;
  onToggle: () => void;
  /** Pre-filled message to auto-send when the popup opens. */
  initialMessage?: string;
  /** Called after the initial message has been consumed (so it won't re-send). */
  onMessageConsumed?: () => void;
}

// Chat bubble SVG icon
const ChatIcon = () => (
  <svg
    className="w-6 h-6"
    fill="none"
    stroke="currentColor"
    strokeWidth="2"
    viewBox="0 0 24 24"
  >
    <path
      strokeLinecap="round"
      strokeLinejoin="round"
      d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z"
    />
  </svg>
);

// X / close icon
const CloseIcon = () => (
  <svg
    className="w-6 h-6"
    fill="none"
    stroke="currentColor"
    strokeWidth="2.5"
    viewBox="0 0 24 24"
  >
    <path
      strokeLinecap="round"
      strokeLinejoin="round"
      d="M6 18L18 6M6 6l12 12"
    />
  </svg>
);

export default function ChatPopup({
  open,
  onToggle,
  initialMessage,
  onMessageConsumed,
}: Props) {
  // Trap focus inside panel when open
  const panelRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (open) {
      // Small delay to allow animation settle before focusing
      setTimeout(() => panelRef.current?.focus(), 50);
    }
  }, [open]);

  return (
    <>
      {/* ── Floating panel ────────────────────────────────────────────── */}
      <div
        ref={panelRef}
        tabIndex={-1}
        aria-hidden={!open}
        className={`
          fixed z-50
          left-2 right-2 top-[60px] bottom-[76px]
          sm:left-auto sm:top-auto sm:right-6 sm:bottom-24
          sm:w-[400px] sm:h-[600px]
          bg-white rounded-2xl shadow-2xl border border-slate-200
          flex flex-col overflow-hidden
          transition-all duration-300 origin-bottom-right outline-none
          ${
            open
              ? "opacity-100 scale-100 pointer-events-auto"
              : "opacity-0 scale-95 pointer-events-none"
          }
        `}
      >
        {/* Panel header */}
        <div className="flex items-center justify-between px-4 py-3 border-b border-slate-100 bg-gradient-to-r from-blue-600 to-indigo-600 shrink-0">
          <div className="flex items-center gap-2.5">
            <span className="flex items-center justify-center w-7 h-7 rounded-full bg-white/20 text-white text-xs font-bold">
              AI
            </span>
            <div>
              <p className="text-sm font-semibold text-white leading-none">
                AI Career Advisor
              </p>
              <p className="text-[10px] text-blue-100 mt-0.5">
                Powered by Gemini · FAISS · 10 000 jobs
              </p>
            </div>
          </div>
          <button
            onClick={onToggle}
            className="rounded-lg p-1 text-white/70 hover:text-white hover:bg-white/10 transition-colors"
            aria-label="Close chat"
          >
            <CloseIcon />
          </button>
        </div>

        {/* Chat body — grows to fill remaining height */}
        <div className="flex-1 overflow-hidden min-h-0">
          <ChatInterface
            className="h-full rounded-none border-0 shadow-none"
            initialMessage={initialMessage}
            onMessageConsumed={onMessageConsumed}
          />
        </div>
      </div>

      {/* ── Toggle button ─────────────────────────────────────────────── */}
      <button
        onClick={onToggle}
        aria-label={open ? "Close AI Advisor" : "Chat with AI Advisor"}
        className={`
          fixed bottom-6 right-6 z-50
          w-14 h-14 rounded-full shadow-lg
          flex items-center justify-center
          transition-all duration-300
          ${
            open
              ? "bg-slate-700 hover:bg-slate-800 rotate-0"
              : "bg-blue-600 hover:bg-blue-700"
          }
          text-white
        `}
      >
        <span
          className={`transition-all duration-200 ${open ? "scale-100" : "scale-100"}`}
        >
          {open ? <CloseIcon /> : <ChatIcon />}
        </span>
        {/* Pulse ring when closed */}
        {!open && (
          <span className="absolute inset-0 rounded-full bg-blue-400 animate-ping opacity-25 pointer-events-none" />
        )}
      </button>
    </>
  );
}
