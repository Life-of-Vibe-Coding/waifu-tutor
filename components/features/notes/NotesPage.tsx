"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { AnimatePresence, motion } from "framer-motion";
import { useCallback, useState } from "react";
import {
  createNote,
  createNoteFolder,
  deleteNote,
  deleteNoteFolder,
  listNoteFolders,
  listNotes,
  updateNote,
  updateNoteFolder,
} from "@/lib/endpoints";
import type { NoteFolder, StudyNote } from "@/types/domain";

const FOLDER_ALL = "__all__";
const FOLDER_UNFILED = "__unfiled__";

export const NotesPage = () => {
  const queryClient = useQueryClient();
  const [selectedFolderId, setSelectedFolderId] = useState<string | null>(FOLDER_ALL);
  const [selectedNoteId, setSelectedNoteId] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const [newFolderName, setNewFolderName] = useState("");
  const [showNewFolder, setShowNewFolder] = useState(false);

  const foldersQuery = useQuery({ queryKey: ["noteFolders"], queryFn: listNoteFolders });
  const folders = foldersQuery.data ?? [];

  const folderFilter =
    selectedFolderId === FOLDER_ALL
      ? undefined
      : selectedFolderId === FOLDER_UNFILED
        ? null
        : selectedFolderId;
  const notesQuery = useQuery({
    queryKey: ["notes", folderFilter],
    queryFn: () => listNotes(folderFilter === null ? null : folderFilter ?? undefined),
  });
  const notes = notesQuery.data ?? [];

  const filteredNotes = search.trim()
    ? notes.filter(
        (n) =>
          n.title.toLowerCase().includes(search.trim().toLowerCase()) ||
          n.content.toLowerCase().includes(search.trim().toLowerCase())
      )
    : notes;

  const selectedNote = selectedNoteId
    ? notes.find((n) => n.id === selectedNoteId)
    : null;

  const createFolderMutation = useMutation({
    mutationFn: (name: string) => createNoteFolder(name),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["noteFolders"] });
      setNewFolderName("");
      setShowNewFolder(false);
    },
  });

  const deleteFolderMutation = useMutation({
    mutationFn: deleteNoteFolder,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["noteFolders"] });
      queryClient.invalidateQueries({ queryKey: ["notes"] });
      if (selectedFolderId && selectedFolderId !== FOLDER_ALL && selectedFolderId !== FOLDER_UNFILED) {
        setSelectedFolderId(FOLDER_ALL);
      }
    },
  });

  const createNoteMutation = useMutation({
    mutationFn: () =>
      createNote({
        title: "新笔记",
        content: "",
        folder_id: folderFilter === undefined ? null : folderFilter,
      }),
    onSuccess: (note) => {
      queryClient.invalidateQueries({ queryKey: ["notes"] });
      setSelectedNoteId(note.id);
    },
  });

  const updateNoteMutation = useMutation({
    mutationFn: ({ id, patch }: { id: string; patch: Parameters<typeof updateNote>[1] }) =>
      updateNote(id, patch),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["notes"] });
    },
  });

  const deleteNoteMutation = useMutation({
    mutationFn: deleteNote,
    onSuccess: (_, deletedId) => {
      queryClient.invalidateQueries({ queryKey: ["notes"] });
      if (selectedNoteId === deletedId) setSelectedNoteId(null);
    },
  });

  const handleSaveNote = useCallback(
    (note: StudyNote, title: string, content: string) => {
      if (title !== note.title || content !== note.content) {
        updateNoteMutation.mutate({
          id: note.id,
          patch: { title: title || "Untitled", content },
        });
      }
    },
    [updateNoteMutation]
  );

  return (
    <section className="flex h-full flex-col overflow-hidden">
      <header className="flex shrink-0 items-center gap-3 border-b border-white/50 bg-white/30 px-4 py-3 backdrop-blur-sm">
        <h1 className="font-display text-xl font-bold tracking-tight text-ink sm:text-2xl">
          学习笔记
        </h1>
      </header>

      <div className="flex min-h-0 flex-1 gap-0 overflow-hidden">
        {/* Folder sidebar */}
        <aside className="flex w-44 shrink-0 flex-col border-r border-white/50 bg-white/20">
          <div className="flex flex-col gap-0.5 p-2">
            <button
              type="button"
              onClick={() => setSelectedFolderId(FOLDER_ALL)}
              className={`rounded-lg px-3 py-2 text-left text-sm font-semibold transition ${
                selectedFolderId === FOLDER_ALL
                  ? "bg-sakura/40 text-ink"
                  : "text-slate-700 hover:bg-white/50"
              }`}
            >
              全部笔记
            </button>
            <button
              type="button"
              onClick={() => setSelectedFolderId(FOLDER_UNFILED)}
              className={`rounded-lg px-3 py-2 text-left text-sm font-semibold transition ${
                selectedFolderId === FOLDER_UNFILED
                  ? "bg-sakura/40 text-ink"
                  : "text-slate-700 hover:bg-white/50"
              }`}
            >
              未分类
            </button>
            {folders.map((f) => (
              <div
                key={f.id}
                className="group flex items-center gap-1 rounded-lg px-2 py-1"
              >
                <button
                  type="button"
                  onClick={() => setSelectedFolderId(f.id)}
                  className={`min-w-0 flex-1 rounded-lg px-2 py-2 text-left text-sm font-semibold transition ${
                    selectedFolderId === f.id
                      ? "bg-aqua/35 text-ink"
                      : "text-slate-700 hover:bg-white/50"
                  }`}
                >
                  <span className="truncate">{f.name}</span>
                </button>
                <button
                  type="button"
                  onClick={() => deleteFolderMutation.mutate(f.id)}
                  className="rounded p-1 text-slate-500 opacity-0 transition hover:bg-rose-200/60 hover:text-rose-800 group-hover:opacity-100"
                  aria-label={`删除文件夹 ${f.name}`}
                >
                  <svg className="h-3.5 w-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </div>
            ))}
            {showNewFolder ? (
              <div className="flex items-center gap-1 px-2 py-1">
                <input
                  type="text"
                  value={newFolderName}
                  onChange={(e) => setNewFolderName(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter") {
                      if (newFolderName.trim()) createFolderMutation.mutate(newFolderName.trim());
                    }
                    if (e.key === "Escape") {
                      setShowNewFolder(false);
                      setNewFolderName("");
                    }
                  }}
                  placeholder="文件夹名"
                  className="min-w-0 flex-1 rounded border border-white/80 bg-white/70 px-2 py-1.5 text-sm text-ink placeholder:text-slate-500 focus:outline-none focus:ring-1 focus:ring-aqua/80"
                  autoFocus
                />
                <button
                  type="button"
                  onClick={() => newFolderName.trim() && createFolderMutation.mutate(newFolderName.trim())}
                  className="rounded bg-aqua/60 px-2 py-1 text-xs font-semibold text-cyan-900"
                >
                  添加
                </button>
              </div>
            ) : (
              <button
                type="button"
                onClick={() => setShowNewFolder(true)}
                className="rounded-lg px-3 py-2 text-left text-sm font-semibold text-slate-600 transition hover:bg-white/50"
              >
                + 新建文件夹
              </button>
            )}
          </div>
        </aside>

        {/* Note list */}
        <div className="flex w-56 shrink-0 flex-col border-r border-white/50 bg-white/15">
          <div className="flex shrink-0 items-center gap-2 border-b border-white/40 p-2">
            <input
              type="search"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="搜索笔记…"
              className="min-w-0 flex-1 rounded-full border border-white/70 bg-white/50 px-3 py-1.5 text-sm text-ink placeholder:text-slate-500 focus:outline-none focus:ring-1 focus:ring-sakura/80"
            />
            <button
              type="button"
              onClick={() => createNoteMutation.mutate()}
              disabled={createNoteMutation.isPending}
              className="shrink-0 rounded-full border border-white/85 bg-gradient-to-br from-sakura/90 to-bubblegum/88 px-3 py-1.5 text-sm font-bold text-rose-900 shadow-sm transition hover:scale-[1.02] disabled:opacity-60"
            >
              + 新建
            </button>
          </div>
          <ul className="min-h-0 flex-1 overflow-y-auto p-2">
            {filteredNotes.length === 0 && (
              <li className="rounded-lg px-3 py-4 text-center text-sm text-slate-500">
                {notes.length === 0 ? "暂无笔记，点击「新建」添加" : "没有匹配的笔记"}
              </li>
            )}
            {filteredNotes.map((note) => (
              <motion.li
                key={note.id}
                layout
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                className="list-none"
              >
                <button
                  type="button"
                  onClick={() => setSelectedNoteId(note.id)}
                  className={`w-full rounded-lg px-3 py-2.5 text-left transition ${
                    selectedNoteId === note.id
                      ? "bg-aqua/40 text-ink ring-1 ring-aqua/60"
                      : "text-slate-800 hover:bg-white/50"
                  }`}
                >
                  <div className="truncate text-sm font-semibold">{note.title || "Untitled"}</div>
                  <div className="mt-0.5 truncate text-xs text-slate-500">
                    {new Date(note.updated_at).toLocaleDateString(undefined, {
                      month: "short",
                      day: "numeric",
                      hour: "2-digit",
                      minute: "2-digit",
                    })}
                  </div>
                </button>
              </motion.li>
            ))}
          </ul>
        </div>

        {/* Note editor */}
        <div className="flex min-w-0 flex-1 flex-col overflow-hidden bg-white/10">
          <AnimatePresence mode="wait">
            {selectedNote ? (
              <NoteEditor
                key={selectedNote.id}
                note={selectedNote}
                onSave={handleSaveNote}
                onDelete={() => deleteNoteMutation.mutate(selectedNote.id)}
                isSaving={updateNoteMutation.isPending}
              />
            ) : (
              <motion.div
                key="empty"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                className="flex flex-1 flex-col items-center justify-center gap-2 text-slate-500"
              >
                <svg className="h-14 w-14 text-slate-300" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                </svg>
                <p className="text-sm font-medium">选择或新建一条笔记</p>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </div>
    </section>
  );
};

interface NoteEditorProps {
  note: StudyNote;
  onSave: (note: StudyNote, title: string, content: string) => void;
  onDelete: () => void;
  isSaving: boolean;
}

const NoteEditor = ({ note, onSave, onDelete, isSaving }: NoteEditorProps) => {
  const [title, setTitle] = useState(note.title);
  const [content, setContent] = useState(note.content);

  const dirty = title !== note.title || content !== note.content;

  const handleBlur = () => {
    if (dirty) onSave(note, title, content);
  };

  return (
    <motion.div
      initial={{ opacity: 0, x: 8 }}
      animate={{ opacity: 1, x: 0 }}
      exit={{ opacity: 0, x: -8 }}
      transition={{ duration: 0.15 }}
      className="flex h-full flex-col overflow-hidden"
    >
      <div className="flex shrink-0 items-center justify-between gap-2 border-b border-white/40 bg-white/20 px-4 py-2">
        <input
          type="text"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          onBlur={handleBlur}
          className="min-w-0 flex-1 rounded-lg border border-white/70 bg-white/60 px-3 py-2 text-base font-bold text-ink placeholder:text-slate-500 focus:outline-none focus:ring-2 focus:ring-sakura/80"
          placeholder="标题"
        />
        <div className="flex items-center gap-1">
          {isSaving && (
            <span className="text-xs text-slate-500">保存中…</span>
          )}
          {dirty && !isSaving && (
            <span className="text-xs text-slate-500">未保存</span>
          )}
          <button
            type="button"
            onClick={() => onSave(note, title, content)}
            disabled={!dirty || isSaving}
            className="rounded-full border border-white/85 bg-aqua/70 px-3 py-1.5 text-sm font-semibold text-cyan-900 disabled:opacity-50"
          >
            保存
          </button>
          <button
            type="button"
            onClick={onDelete}
            className="rounded-full border border-white/70 bg-rose-200/60 px-3 py-1.5 text-sm font-semibold text-rose-800 transition hover:bg-rose-300/70"
          >
            删除
          </button>
        </div>
      </div>
      <textarea
        value={content}
        onChange={(e) => setContent(e.target.value)}
        onBlur={handleBlur}
        placeholder="写下你的笔记…"
        className="min-h-0 flex-1 resize-none rounded-none border-0 border-white/30 bg-transparent px-4 py-3 text-sm leading-relaxed text-ink placeholder:text-slate-500 focus:outline-none focus:ring-0"
        spellCheck
      />
    </motion.div>
  );
};
