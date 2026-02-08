import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useMemo, useState } from "react";

import { generateFlashcards, listDocuments, listFlashcards, reviewFlashcard } from "../../api/endpoints";
import { useAppStore } from "../../state/appStore";

export const FlashcardsPage = () => {
  const queryClient = useQueryClient();
  const [currentIndex, setCurrentIndex] = useState(0);
  const [showAnswer, setShowAnswer] = useState(false);

  const activeDocId = useAppStore((state) => state.activeDocId);
  const setActiveDocId = useAppStore((state) => state.setActiveDocId);
  const setMood = useAppStore((state) => state.setMood);

  const docsQuery = useQuery({ queryKey: ["documents"], queryFn: listDocuments });
  const cardsQuery = useQuery({
    queryKey: ["flashcards", activeDocId],
    queryFn: () => listFlashcards(activeDocId ?? ""),
    enabled: Boolean(activeDocId),
  });

  const generateMutation = useMutation({
    mutationFn: () => generateFlashcards(activeDocId ?? ""),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["flashcards", activeDocId] });
      setMood("excited");
      setCurrentIndex(0);
      setShowAnswer(false);
    },
    onError: () => setMood("sad"),
  });

  const reviewMutation = useMutation({
    mutationFn: ({ cardId, quality }: { cardId: string; quality: number }) => reviewFlashcard(cardId, quality),
    onSuccess: async (_, variables) => {
      await queryClient.invalidateQueries({ queryKey: ["flashcards", activeDocId] });
      setMood(variables.quality >= 4 ? "happy" : "encouraging");
      setShowAnswer(false);
      setCurrentIndex((prev) => prev + 1);
    },
    onError: () => setMood("sad"),
  });

  const cards = cardsQuery.data ?? [];
  const card = cards[currentIndex] ?? null;
  const progress = useMemo(() => {
    if (!cards.length) {
      return 0;
    }
    return Math.min(100, Math.round((currentIndex / cards.length) * 100));
  }, [cards.length, currentIndex]);

  return (
    <section className="space-y-4">
      <div className="rounded-2xl bg-white p-4 shadow-soft">
        <h2 className="font-display text-2xl">Flashcards</h2>
        <div className="mt-3 flex flex-wrap items-center gap-2">
          <select
            value={activeDocId ?? ""}
            onChange={(event) => {
              setActiveDocId(event.target.value || null);
              setCurrentIndex(0);
              setShowAnswer(false);
            }}
            className="rounded-lg border border-slate-300 px-3 py-2"
          >
            <option value="">Select a document</option>
            {(docsQuery.data ?? []).map((doc) => (
              <option key={doc.id} value={doc.id}>
                {doc.title}
              </option>
            ))}
          </select>
          <button
            type="button"
            onClick={() => generateMutation.mutate()}
            disabled={!activeDocId || generateMutation.isPending}
            className="rounded-full bg-accent px-4 py-2 text-sm font-semibold text-white disabled:opacity-60"
          >
            {generateMutation.isPending ? "Generating" : "Generate Cards"}
          </button>
        </div>

        <div className="mt-3 h-2 w-full overflow-hidden rounded-full bg-slate-200">
          <div className="h-full bg-calm transition-all" style={{ width: `${progress}%` }} />
        </div>
      </div>

      <div className="rounded-2xl bg-white p-4 shadow-soft">
        {!card && <p className="text-sm text-slate-600">No cards yet for this document.</p>}

        {card && (
          <div className="space-y-4">
            <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
              <p className="text-xs uppercase tracking-wide text-slate-500">Question</p>
              <p className="mt-1 text-lg font-semibold">{card.question}</p>
              {showAnswer && (
                <>
                  <p className="mt-3 text-xs uppercase tracking-wide text-slate-500">Answer</p>
                  <p className="mt-1 text-base">{card.answer}</p>
                  {card.explanation && <p className="mt-1 text-sm text-slate-700">{card.explanation}</p>}
                </>
              )}
            </div>

            <div className="flex flex-wrap gap-2">
              <button
                type="button"
                onClick={() => setShowAnswer((prev) => !prev)}
                className="rounded-full bg-slate-100 px-3 py-2 text-sm font-semibold"
              >
                {showAnswer ? "Hide" : "Show"} Answer
              </button>

              {showAnswer && (
                <>
                  {[2, 3, 4, 5].map((quality) => (
                    <button
                      key={quality}
                      type="button"
                      onClick={() => reviewMutation.mutate({ cardId: card.id, quality })}
                      className="rounded-full bg-calm px-3 py-2 text-sm font-semibold text-white"
                    >
                      Score {quality}
                    </button>
                  ))}
                </>
              )}
            </div>

            <p className="text-xs text-slate-500">
              Repetitions: {card.repetitions} • Next review: {card.next_review_at ?? "now"}
            </p>
          </div>
        )}
      </div>
    </section>
  );
};
