import { useMutation, useQuery } from "@tanstack/react-query";
import { useState } from "react";

import { listDocuments, summarizeDocument } from "../../api/endpoints";
import { speakText } from "../../lib/tts";
import { useAppStore } from "../../state/appStore";

export const SummaryPage = () => {
  const activeDocId = useAppStore((state) => state.activeDocId);
  const setActiveDocId = useAppStore((state) => state.setActiveDocId);
  const setMood = useAppStore((state) => state.setMood);
  const ttsEnabled = useAppStore((state) => state.ttsEnabled);

  const [detail, setDetail] = useState<"short" | "medium" | "detailed">("medium");

  const docsQuery = useQuery({ queryKey: ["documents"], queryFn: listDocuments });

  const summaryMutation = useMutation({
    mutationFn: (docId: string) => summarizeDocument(docId, detail),
    onSuccess: (result) => {
      setMood("happy");
      if (ttsEnabled) {
        speakText(result.summary_text);
      }
    },
    onError: () => setMood("sad"),
  });

  return (
    <section className="space-y-4">
      <div className="rounded-2xl bg-white p-4 shadow-soft">
        <h2 className="font-display text-2xl">Summary</h2>
        <div className="mt-3 grid gap-3 md:grid-cols-[1fr_auto_auto]">
          <select
            value={activeDocId ?? ""}
            onChange={(event) => setActiveDocId(event.target.value || null)}
            className="rounded-lg border border-slate-300 px-3 py-2"
          >
            <option value="">Select a document</option>
            {(docsQuery.data ?? []).map((doc) => (
              <option key={doc.id} value={doc.id}>
                {doc.title}
              </option>
            ))}
          </select>

          <select
            value={detail}
            onChange={(event) => setDetail(event.target.value as "short" | "medium" | "detailed")}
            className="rounded-lg border border-slate-300 px-3 py-2"
          >
            <option value="short">Short</option>
            <option value="medium">Medium</option>
            <option value="detailed">Detailed</option>
          </select>

          <button
            type="button"
            onClick={() => activeDocId && summaryMutation.mutate(activeDocId)}
            disabled={!activeDocId || summaryMutation.isPending}
            className="rounded-full bg-calm px-4 py-2 font-semibold text-white disabled:opacity-60"
          >
            {summaryMutation.isPending ? "Generating..." : "Generate"}
          </button>
        </div>
      </div>

      {summaryMutation.data && (
        <article className="rounded-2xl bg-white p-4 shadow-soft">
          <div className="mb-3 flex items-center justify-between">
            <h3 className="text-lg font-semibold">Summary Output</h3>
            <div className="flex gap-2">
              {summaryMutation.data.cached && (
                <span className="rounded bg-slate-100 px-2 py-1 text-xs font-medium text-slate-700">cached</span>
              )}
              <button
                type="button"
                onClick={() => speakText(summaryMutation.data.summary_text)}
                className="rounded bg-accent px-3 py-1 text-xs font-semibold text-white"
              >
                Read Aloud
              </button>
            </div>
          </div>
          <pre className="whitespace-pre-wrap text-sm leading-6 text-slate-800">{summaryMutation.data.summary_text}</pre>
        </article>
      )}
    </section>
  );
};
