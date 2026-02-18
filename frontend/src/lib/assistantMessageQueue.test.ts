import { describe, expect, it } from "vitest";
import { AssistantMessageQueue } from "./assistantMessageQueue";

describe("AssistantMessageQueue", () => {
  it("coalesces chunks from the same stream into one entry", () => {
    let now = 0;
    const queue = new AssistantMessageQueue({ cooldownMs: 3000, now: () => now });

    const first = queue.enqueueChunk("sse-1", "hello");
    expect(first.map((x) => x.type)).toEqual(["started"]);
    expect(first[0]?.entry.text).toBe("hello");

    const second = queue.enqueueChunk("sse-1", "world");
    expect(second.map((x) => x.type)).toEqual(["updated"]);
    expect(second[0]?.entry.text).toBe("hello world");

    const snapshot = queue.snapshot();
    expect(snapshot.order).toEqual(["sse-1"]);
    expect(snapshot.entries).toHaveLength(1);
    expect(snapshot.entries[0]?.text).toBe("hello world");
  });

  it("preserves first-in queue order for interleaved streams", () => {
    let now = 0;
    const queue = new AssistantMessageQueue({ cooldownMs: 0, now: () => now });

    queue.enqueueChunk("sse-1", "chunk1");
    queue.enqueueChunk("sse-2", "chunkA");
    queue.enqueueChunk("sse-1", "chunk2");

    const beforeDone = queue.snapshot();
    expect(beforeDone.order).toEqual(["sse-1", "sse-2"]);
    expect(beforeDone.entries[0]?.text).toBe("chunk1 chunk2");
    expect(beforeDone.entries[1]?.text).toBe("chunkA");

    const doneActions = queue.markDone("sse-1");
    expect(doneActions.map((x) => x.type)).toEqual(["updated", "completed", "started"]);
    expect(doneActions[2]?.entry.streamId).toBe("sse-2");
  });

  it("waits for stream done and 3s cooldown before starting next stream", () => {
    let now = 0;
    const queue = new AssistantMessageQueue({ cooldownMs: 3000, now: () => now });

    queue.enqueueChunk("sse-1", "first");
    queue.enqueueChunk("sse-2", "second");

    const doneActions = queue.markDone("sse-1", "first complete");
    expect(doneActions.map((x) => x.type)).toEqual(["updated", "completed"]);
    expect(queue.snapshot().activeStreamId).toBeNull();

    now = 2000;
    expect(queue.tick()).toEqual([]);
    expect(queue.snapshot().activeStreamId).toBeNull();

    now = 3000;
    const startSecond = queue.tick();
    expect(startSecond.map((x) => x.type)).toEqual(["started"]);
    expect(startSecond[0]?.entry.streamId).toBe("sse-2");
  });

  it("routes local/system messages through same cooldown gate", () => {
    let now = 0;
    const queue = new AssistantMessageQueue({ cooldownMs: 3000, now: () => now });

    const localActions = queue.enqueueLocalMessage("local-ack", "Well received!", "local");
    expect(localActions.map((x) => x.type)).toEqual(["started", "completed"]);

    now = 1000;
    const sseActions = queue.enqueueChunk("sse-1", "next reply");
    expect(sseActions).toEqual([]);
    expect(queue.snapshot().order).toEqual(["sse-1"]);
    expect(queue.snapshot().activeStreamId).toBeNull();

    now = 3000;
    const startActions = queue.tick();
    expect(startActions.map((x) => x.type)).toEqual(["started"]);
    expect(startActions[0]?.entry.streamId).toBe("sse-1");
  });
});
