import { useAppStore } from "../state/appStore";
import { Live2DCharacter } from "./Live2DCharacter";

export const CharacterPanel = () => {
  const mood = useAppStore((state) => state.mood);

  return (
    <aside className="sticky top-5 hidden h-[calc(100vh-2.5rem)] min-w-[340px] flex-col items-center gap-3 rounded-3xl border border-white/70 bg-panel/80 p-4 shadow-soft lg:flex">
      <div className="w-full flex-1">
        <Live2DCharacter mood={mood} />
      </div>
      <p className="text-center text-xs text-slate-700">
        Uses Live2D Cubism Web sample build when available at <code>/live2d-demo</code>. Fallback
        renderer is shown otherwise.
      </p>
    </aside>
  );
};
