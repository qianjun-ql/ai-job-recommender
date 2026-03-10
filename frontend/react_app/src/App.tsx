/**
 * App — top-level shell.
 * LandingPage owns its full-page layout (nav, hero, sections, footer).
 * ChatPopup is always rendered as a floating layer and can be opened from
 * the landing page via onNavigate("chat").
 */
import LandingPage from "@/pages/landing-page/landing-page";
import ChatPopup from "@/components/chat-popup/chat-popup";
import { useState } from "react";

export default function App() {
  const [chatOpen, setChatOpen] = useState(false);
  const [chatInitialMsg, setChatInitialMsg] = useState("");

  const handleNavigate = (tab: "analyze" | "chat") => {
    // "analyze" is retired — route everything to the AI chat advisor
    if (tab === "analyze" || tab === "chat") {
      setChatOpen(true);
    }
  };

  const handleChatMessage = (msg: string) => {
    setChatInitialMsg(msg);
    setChatOpen(true);
  };

  return (
    <>
      <LandingPage
        onNavigate={handleNavigate}
        onChatMessage={handleChatMessage}
      />
      <ChatPopup
        open={chatOpen}
        onToggle={() => setChatOpen((o) => !o)}
        initialMessage={chatInitialMsg}
        onMessageConsumed={() => setChatInitialMsg("")}
      />
    </>
  );
}
