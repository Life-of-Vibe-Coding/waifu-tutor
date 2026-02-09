import { ChatPage } from "../features/chat/ChatPage";
import { CompanionHud } from "./cute/CompanionHud";
import { Live2DStage } from "./Live2DStage";

export const AppShell = () => {
  return (
    <div className="relative isolate min-h-screen overflow-hidden">
      <Live2DStage />
      <div className="absolute inset-0 z-20">
        <ChatPage />
      </div>
      <div className="pointer-events-none absolute inset-0 z-30">
        <div className="pointer-events-auto absolute right-3 top-3 sm:right-6 sm:top-6">
          <CompanionHud />
        </div>
      </div>
    </div>
  );
};
