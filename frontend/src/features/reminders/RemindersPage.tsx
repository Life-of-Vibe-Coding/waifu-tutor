import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { FormEvent, useEffect, useRef, useState } from "react";

import { createReminder, deleteReminder, listReminders, updateReminder } from "../../api/endpoints";
import { useAppStore } from "../../state/appStore";

export const RemindersPage = () => {
  const queryClient = useQueryClient();
  const setMood = useAppStore((state) => state.setMood);

  const [title, setTitle] = useState("");
  const [note, setNote] = useState("");
  const [scheduledFor, setScheduledFor] = useState("");
  const notified = useRef<Set<string>>(new Set());

  const remindersQuery = useQuery({
    queryKey: ["reminders"],
    queryFn: listReminders,
    refetchInterval: 30000,
  });

  const createMutation = useMutation({
    mutationFn: (payload: { title: string; note: string; scheduledFor: string }) =>
      createReminder(payload.title, payload.note, payload.scheduledFor),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["reminders"] });
      setMood("happy");
      setTitle("");
      setNote("");
      setScheduledFor("");
    },
    onError: () => setMood("sad"),
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, completed }: { id: string; completed: boolean }) => updateReminder(id, { completed }),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["reminders"] });
    },
  });

  const deleteMutation = useMutation({
    mutationFn: deleteReminder,
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["reminders"] });
    },
  });

  useEffect(() => {
    if (Notification.permission !== "granted") {
      return;
    }

    for (const reminder of remindersQuery.data ?? []) {
      if (reminder.due_now && !reminder.completed && !notified.current.has(reminder.id)) {
        new Notification(`Study reminder: ${reminder.title}`, {
          body: reminder.note || "It's time for your next study session.",
        });
        notified.current.add(reminder.id);
      }
    }
  }, [remindersQuery.data]);

  const requestPermission = async () => {
    if (typeof Notification === "undefined") {
      return;
    }
    const result = await Notification.requestPermission();
    if (result === "granted") {
      setMood("excited");
    }
  };

  const handleCreate = (event: FormEvent) => {
    event.preventDefault();
    if (!title || !scheduledFor) {
      return;
    }
    createMutation.mutate({
      title,
      note,
      scheduledFor: new Date(scheduledFor).toISOString(),
    });
  };

  return (
    <section className="space-y-4">
      <div className="rounded-2xl bg-white p-4 shadow-soft">
        <h2 className="font-display text-2xl">Reminders</h2>
        <p className="mb-3 text-sm text-slate-600">Browser notifications are used for due reminders.</p>

        <div className="mb-4">
          <button
            type="button"
            onClick={() => void requestPermission()}
            className="rounded-full bg-calm px-4 py-2 text-sm font-semibold text-white"
          >
            Request Notification Permission
          </button>
        </div>

        <form onSubmit={handleCreate} className="grid gap-2 md:grid-cols-4">
          <input
            value={title}
            onChange={(event) => setTitle(event.target.value)}
            placeholder="Reminder title"
            className="rounded-lg border border-slate-300 px-3 py-2"
          />
          <input
            value={note}
            onChange={(event) => setNote(event.target.value)}
            placeholder="Optional note"
            className="rounded-lg border border-slate-300 px-3 py-2"
          />
          <input
            type="datetime-local"
            value={scheduledFor}
            onChange={(event) => setScheduledFor(event.target.value)}
            className="rounded-lg border border-slate-300 px-3 py-2"
          />
          <button type="submit" className="rounded-full bg-accent px-4 py-2 font-semibold text-white">
            Create
          </button>
        </form>
      </div>

      <div className="rounded-2xl bg-white p-4 shadow-soft">
        <h3 className="mb-3 text-lg font-semibold">Scheduled Items</h3>
        <div className="space-y-2">
          {(remindersQuery.data ?? []).map((reminder) => (
            <div key={reminder.id} className="rounded-xl border border-slate-200 p-3">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <div>
                  <p className="font-semibold">{reminder.title}</p>
                  <p className="text-sm text-slate-600">{reminder.note}</p>
                  <p className="text-xs text-slate-500">{new Date(reminder.scheduled_for).toLocaleString()}</p>
                </div>
                <div className="flex items-center gap-2">
                  <button
                    type="button"
                    onClick={() => updateMutation.mutate({ id: reminder.id, completed: !reminder.completed })}
                    className="rounded-full bg-slate-100 px-3 py-1 text-xs font-semibold"
                  >
                    {reminder.completed ? "Reopen" : "Complete"}
                  </button>
                  <button
                    type="button"
                    onClick={() => deleteMutation.mutate(reminder.id)}
                    className="rounded-full bg-red-100 px-3 py-1 text-xs font-semibold text-red-700"
                  >
                    Delete
                  </button>
                </div>
              </div>
              {reminder.due_now && !reminder.completed && (
                <p className="mt-2 text-xs font-semibold text-amber-700">Due now</p>
              )}
            </div>
          ))}
          {!remindersQuery.isLoading && (remindersQuery.data?.length ?? 0) === 0 && (
            <p className="text-sm text-slate-600">No reminders yet.</p>
          )}
        </div>
      </div>
    </section>
  );
};
