import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useMemo, useState } from "react";

import { listDocuments, uploadDocument } from "../../api/endpoints";
import { useAppStore } from "../../state/appStore";

export const DocumentsPage = () => {
  const queryClient = useQueryClient();
  const setActiveDocId = useAppStore((state) => state.setActiveDocId);
  const activeDocId = useAppStore((state) => state.activeDocId);
  const setMood = useAppStore((state) => state.setMood);

  const [selectedFile, setSelectedFile] = useState<File | null>(null);

  const docsQuery = useQuery({
    queryKey: ["documents"],
    queryFn: listDocuments,
  });

  const uploadMutation = useMutation({
    mutationFn: uploadDocument,
    onSuccess: async (doc) => {
      await queryClient.invalidateQueries({ queryKey: ["documents"] });
      setActiveDocId(doc.id);
      setMood("excited");
      setSelectedFile(null);
    },
    onError: () => {
      setMood("sad");
    },
  });

  const readyDocs = useMemo(() => docsQuery.data?.filter((doc) => doc.status === "ready") ?? [], [docsQuery.data]);

  return (
    <section className="space-y-5">
      <div className="rounded-2xl bg-white p-4 shadow-soft">
        <h2 className="font-display text-2xl">Upload Document</h2>
        <p className="mb-4 text-sm text-slate-600">Supports PDF, DOCX, TXT, and MD files.</p>
        <div className="flex flex-wrap items-center gap-3">
          <input
            type="file"
            accept=".pdf,.docx,.txt,.md"
            onChange={(event) => setSelectedFile(event.target.files?.[0] ?? null)}
            className="rounded border border-slate-300 bg-white px-3 py-2 text-sm"
          />
          <button
            type="button"
            onClick={() => selectedFile && uploadMutation.mutate(selectedFile)}
            disabled={!selectedFile || uploadMutation.isPending}
            className="rounded-full bg-accent px-4 py-2 text-sm font-semibold text-white disabled:cursor-not-allowed disabled:opacity-60"
          >
            {uploadMutation.isPending ? "Uploading..." : "Upload"}
          </button>
        </div>
        {uploadMutation.error && (
          <p className="mt-2 text-sm text-red-600">Upload failed. Check file type, size, and backend logs.</p>
        )}
      </div>

      <div className="rounded-2xl bg-white p-4 shadow-soft">
        <h3 className="mb-3 text-lg font-semibold">Your Documents</h3>
        <div className="space-y-2">
          {(docsQuery.data ?? []).map((doc) => (
            <button
              key={doc.id}
              type="button"
              onClick={() => setActiveDocId(doc.id)}
              className={`w-full rounded-xl border px-3 py-3 text-left transition ${
                activeDocId === doc.id ? "border-accent bg-orange-50" : "border-slate-200 bg-white"
              }`}
            >
              <div className="flex items-center justify-between">
                <span className="font-semibold">{doc.title}</span>
                <span className="text-xs uppercase tracking-wide text-slate-500">{doc.status}</span>
              </div>
              <p className="text-sm text-slate-600">
                {doc.word_count} words {doc.topic_hint ? `• ${doc.topic_hint}` : ""}
              </p>
            </button>
          ))}

          {!docsQuery.isLoading && (docsQuery.data?.length ?? 0) === 0 && (
            <p className="text-sm text-slate-600">No documents yet. Upload one to start a study flow.</p>
          )}
        </div>
      </div>

      <p className="text-sm text-slate-700">
        Ready documents: <span className="font-semibold">{readyDocs.length}</span>
      </p>
    </section>
  );
};
