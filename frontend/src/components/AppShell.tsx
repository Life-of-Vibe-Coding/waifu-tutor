import { useAppStore } from "../state/appStore";
import { ChatPage } from "../features/chat/ChatPage";
import { CharacterPanel } from "./CharacterPanel";

export const AppShell = () => {
  const ttsEnabled = useAppStore((state) => state.ttsEnabled);
  const toggleTts = useAppStore((state) => state.toggleTts);

  return (
    <div className="mx-auto grid min-h-screen max-w-7xl grid-cols-1 gap-5 p-5 lg:grid-cols-[1fr_minmax(340px,420px)]">
      <div className="space-y-4">
        <header className="rounded-3xl border border-white/70 bg-panel/90 p-5 shadow-soft">
          <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
            <div>
              <h1 className="font-display text-3xl text-ink">Waifu Tutor</h1>
              <p className="text-slate-700">Chat with your tutor companion.</p>
            </div>
            <button
              type="button"
              onClick={toggleTts}
              className={`rounded-full px-4 py-2 text-sm font-semibold transition ${
                ttsEnabled ? "bg-calm text-white" : "bg-slate-200 text-slate-700"
              }`}
            >
              Voice {ttsEnabled ? "On" : "Off"}
            </button>
          </div>
        </header>

        <main className="rounded-3xl border border-white/70 bg-panel/85 p-5 shadow-soft">
          <ChatPage />
        </main>
      </div>

      <CharacterPanel />
    </div>
  );
};
