import { useRef, useState } from "react";

import { chat, streamChat } from "../../api/endpoints";
import { speakText } from "../../lib/tts";
import { useAppStore } from "../../state/appStore";

export const ChatPage = () => {
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const activeDocId = useAppStore((state) => state.activeDocId);
  const ttsEnabled = useAppStore((state) => state.ttsEnabled);
  const messages = useAppStore((state) => state.messages);
  const setMessages = useAppStore((state) => state.setMessages);
  const setMood = useAppStore((state) => state.setMood);

  const messagesEndRef = useRef<HTMLDivElement | null>(null);

  const send = async () => {
    if (!input.trim() || loading) {
      return;
    }

    setLoading(true);
    setError(null);

    const userMessage = { role: "user" as const, content: input.trim() };
    const history = [...messages, userMessage];
    setMessages([...history, { role: "assistant", content: "" }]);
    setInput("");

    let assistantText = "";

    try {
      await streamChat(userMessage.content, history, activeDocId, (event) => {
        if (event.type === "token") {
          assistantText = `${assistantText} ${String(event.payload.token)}`.trim();
          setMessages([...history, { role: "assistant", content: assistantText }]);
        }

        if (event.type === "mood") {
          setMood(event.payload.mood);
        }

        if (event.type === "done") {
          const finalMessage = String(event.payload.message ?? assistantText);
          setMessages([...history, { role: "assistant", content: finalMessage }]);
          if (ttsEnabled) {
            speakText(finalMessage);
          }
          setMood("encouraging");
        }
      });
    } catch {
      try {
        const response = await chat(userMessage.content, history, activeDocId);
        setMessages([...history, response.message]);
        setMood(response.mood);
        if (ttsEnabled) {
          speakText(response.message.content);
        }
      } catch {
        setError("Failed to get response from assistant.");
        setMood("sad");
      }
    } finally {
      setLoading(false);
      setTimeout(() => messagesEndRef.current?.scrollIntoView({ behavior: "smooth" }), 30);
    }
  };

  return (
    <section>
      <div className="flex min-h-[560px] flex-col rounded-2xl bg-white p-4 shadow-soft">
        <h2 className="mb-3 font-display text-2xl">Chat</h2>

        <div className="flex-1 space-y-3 overflow-y-auto rounded-xl border border-slate-200 bg-slate-50 p-3">
          {messages.map((message, index) => (
            <div
              key={`${message.role}-${index}`}
              className={`max-w-[90%] rounded-xl px-3 py-2 text-sm ${
                message.role === "user" ? "ml-auto bg-accent text-white" : "bg-white text-slate-800"
              }`}
            >
              {message.content || (message.role === "assistant" ? "..." : "")}
            </div>
          ))}
          <div ref={messagesEndRef} />
        </div>

        <div className="mt-3 flex gap-2">
          <input
            value={input}
            onChange={(event) => setInput(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === "Enter") {
                event.preventDefault();
                void send();
              }
            }}
            placeholder="Ask anything..."
            className="flex-1 rounded-xl border border-slate-300 px-3 py-2"
          />
          <button
            type="button"
            onClick={() => void send()}
            disabled={loading}
            className="rounded-full bg-calm px-4 py-2 text-sm font-semibold text-white disabled:opacity-60"
          >
            {loading ? "Sending" : "Send"}
          </button>
        </div>

        {error && <p className="mt-2 text-sm text-red-600">{error}</p>}
        {!activeDocId && <p className="mt-2 text-xs text-slate-500">No document context selected.</p>}
      </div>
    </section>
  );
};
