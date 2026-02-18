import type { CharacterMood } from "@/types/domain";
import type { ReminderPayload } from "./endpoints";

export type AssistantQueueSource = "sse" | "local" | "system";

export interface AssistantQueueMeta {
  mood?: CharacterMood;
  reminder?: ReminderPayload;
  sessionId?: string | null;
}

export interface AssistantQueueEntrySnapshot {
  streamId: string;
  source: AssistantQueueSource;
  text: string;
  isDone: boolean;
  enqueuedAt: number;
  completedAt?: number;
  startedAt?: number;
  meta: AssistantQueueMeta;
}

export type AssistantQueueAction =
  | { type: "started"; entry: AssistantQueueEntrySnapshot }
  | { type: "updated"; entry: AssistantQueueEntrySnapshot }
  | { type: "completed"; entry: AssistantQueueEntrySnapshot };

interface QueueEntry {
  streamId: string;
  source: AssistantQueueSource;
  text: string;
  isDone: boolean;
  enqueuedAt: number;
  completedAt?: number;
  startedAt?: number;
  meta: AssistantQueueMeta;
}

export interface AssistantQueueStateSnapshot {
  activeStreamId: string | null;
  nextAllowedAt: number;
  order: string[];
  entries: AssistantQueueEntrySnapshot[];
}

const DEFAULT_COOLDOWN_MS = 3000;

const appendChunk = (base: string, chunk: string): string => {
  const cleaned = String(chunk ?? "").trim();
  if (!cleaned) return base;
  return `${base} ${cleaned}`.trim();
};

const mergeMeta = (target: AssistantQueueMeta, patch?: AssistantQueueMeta): AssistantQueueMeta => {
  if (!patch) return target;
  return { ...target, ...patch };
};

export class AssistantMessageQueue {
  private readonly cooldownMs: number;
  private readonly now: () => number;
  private readonly entries = new Map<string, QueueEntry>();
  private order: string[] = [];
  private activeStreamId: string | null = null;
  private nextAllowedAt = 0;

  constructor(options?: { cooldownMs?: number; now?: () => number }) {
    this.cooldownMs = Math.max(0, options?.cooldownMs ?? DEFAULT_COOLDOWN_MS);
    this.now = options?.now ?? (() => Date.now());
  }

  enqueueChunk(streamId: string, chunk: string, source: AssistantQueueSource = "sse"): AssistantQueueAction[] {
    const at = this.now();
    const entry = this.ensureEntry(streamId, source, at);
    entry.text = appendChunk(entry.text, chunk);

    const actions: AssistantQueueAction[] = [];
    if (this.activeStreamId === streamId) {
      actions.push({ type: "updated", entry: this.snapshotEntry(entry) });
    }
    this.runStateMachine(at, actions);
    return actions;
  }

  enqueueLocalMessage(
    streamId: string,
    content: string,
    source: AssistantQueueSource = "local",
    meta?: AssistantQueueMeta
  ): AssistantQueueAction[] {
    const at = this.now();
    const entry = this.ensureEntry(streamId, source, at);
    entry.text = appendChunk(entry.text, content);
    entry.meta = mergeMeta(entry.meta, meta);
    entry.isDone = true;
    if (!entry.completedAt) entry.completedAt = at;
    const actions: AssistantQueueAction[] = [];
    this.runStateMachine(at, actions);
    return actions;
  }

  upsertMeta(streamId: string, meta: AssistantQueueMeta, source: AssistantQueueSource = "sse"): AssistantQueueAction[] {
    const at = this.now();
    const entry = this.ensureEntry(streamId, source, at);
    entry.meta = mergeMeta(entry.meta, meta);
    const actions: AssistantQueueAction[] = [];
    this.runStateMachine(at, actions);
    return actions;
  }

  markDone(streamId: string, finalMessage?: string, meta?: AssistantQueueMeta): AssistantQueueAction[] {
    const at = this.now();
    const entry = this.ensureEntry(streamId, "sse", at);
    if (typeof finalMessage === "string" && finalMessage.trim()) {
      entry.text = finalMessage.trim();
    }
    entry.meta = mergeMeta(entry.meta, meta);
    entry.isDone = true;
    if (!entry.completedAt) entry.completedAt = at;

    const actions: AssistantQueueAction[] = [];
    if (this.activeStreamId === streamId) {
      actions.push({ type: "updated", entry: this.snapshotEntry(entry) });
    }
    this.runStateMachine(at, actions);
    return actions;
  }

  tick(): AssistantQueueAction[] {
    const at = this.now();
    const actions: AssistantQueueAction[] = [];
    this.runStateMachine(at, actions);
    return actions;
  }

  clear(): void {
    this.entries.clear();
    this.order = [];
    this.activeStreamId = null;
    this.nextAllowedAt = 0;
  }

  snapshot(): AssistantQueueStateSnapshot {
    const entries = this.order
      .map((streamId) => this.entries.get(streamId))
      .filter((entry): entry is QueueEntry => !!entry)
      .map((entry) => this.snapshotEntry(entry));
    return {
      activeStreamId: this.activeStreamId,
      nextAllowedAt: this.nextAllowedAt,
      order: [...this.order],
      entries,
    };
  }

  private ensureEntry(streamId: string, source: AssistantQueueSource, enqueuedAt: number): QueueEntry {
    const id = String(streamId || "").trim();
    if (!id) throw new Error("streamId is required");

    const existing = this.entries.get(id);
    if (existing) return existing;

    const entry: QueueEntry = {
      streamId: id,
      source,
      text: "",
      isDone: false,
      enqueuedAt,
      meta: {},
    };
    this.entries.set(id, entry);
    this.order.push(id);
    return entry;
  }

  private runStateMachine(now: number, actions: AssistantQueueAction[]): void {
    if (!this.activeStreamId) {
      this.startNextIfAllowed(now, actions);
    }

    if (!this.activeStreamId) return;
    const active = this.entries.get(this.activeStreamId);
    if (!active) {
      this.activeStreamId = null;
      this.startNextIfAllowed(now, actions);
      return;
    }

    if (!active.isDone) return;

    if (!active.completedAt) active.completedAt = now;
    actions.push({ type: "completed", entry: this.snapshotEntry(active) });

    this.nextAllowedAt = Math.max(this.nextAllowedAt, active.completedAt + this.cooldownMs);
    this.entries.delete(active.streamId);
    this.order = this.order.filter((id) => id !== active.streamId);
    this.activeStreamId = null;

    if (now >= this.nextAllowedAt) {
      this.startNextIfAllowed(now, actions);
      if (this.activeStreamId) {
        const next = this.entries.get(this.activeStreamId);
        if (next?.isDone) {
          this.runStateMachine(now, actions);
        }
      }
    }
  }

  private startNextIfAllowed(now: number, actions: AssistantQueueAction[]): void {
    if (this.activeStreamId || now < this.nextAllowedAt) return;
    const nextId = this.order[0];
    if (!nextId) return;
    const entry = this.entries.get(nextId);
    if (!entry) {
      this.order = this.order.filter((id) => id !== nextId);
      return;
    }
    this.activeStreamId = nextId;
    if (!entry.startedAt) entry.startedAt = now;
    actions.push({ type: "started", entry: this.snapshotEntry(entry) });
  }

  private snapshotEntry(entry: QueueEntry): AssistantQueueEntrySnapshot {
    return {
      streamId: entry.streamId,
      source: entry.source,
      text: entry.text,
      isDone: entry.isDone,
      enqueuedAt: entry.enqueuedAt,
      completedAt: entry.completedAt,
      startedAt: entry.startedAt,
      meta: { ...entry.meta },
    };
  }
}
