import { describe, expect, it } from "vitest";
import { parseSseFrames, readSseStream } from "./sse";

describe("parseSseFrames", () => {
  it("parses a single complete frame", () => {
    const { frames, rest } = parseSseFrames('event: token\ndata: {"text":"hi"}\n\n');
    expect(frames).toEqual([{ event: "token", data: { text: "hi" } }]);
    expect(rest).toBe("");
  });

  it("parses multiple frames in one buffer", () => {
    const buf =
      'event: token\ndata: {"text":"a"}\n\n' + 'event: token\ndata: {"text":"b"}\n\n';
    const { frames, rest } = parseSseFrames(buf);
    expect(frames).toHaveLength(2);
    expect(frames[0].data).toEqual({ text: "a" });
    expect(frames[1].data).toEqual({ text: "b" });
    expect(rest).toBe("");
  });

  it("keeps a trailing partial frame in the buffer", () => {
    const buf = 'event: token\ndata: {"text":"a"}\n\n' + 'event: token\ndata: {"tex';
    const { frames, rest } = parseSseFrames(buf);
    expect(frames).toHaveLength(1);
    expect(rest).toBe('event: token\ndata: {"tex');
  });

  it("reassembles a frame split mid-chunk once the rest arrives", () => {
    const first = parseSseFrames('event: token\ndata: {"tex');
    expect(first.frames).toHaveLength(0);
    const second = parseSseFrames(first.rest + 't":"hi"}\n\n');
    expect(second.frames).toEqual([{ event: "token", data: { text: "hi" } }]);
  });

  it("skips a frame with unparsable JSON rather than throwing", () => {
    const buf = "event: token\ndata: {not json}\n\n" + 'event: token\ndata: {"text":"ok"}\n\n';
    const { frames } = parseSseFrames(buf);
    expect(frames).toEqual([{ event: "token", data: { text: "ok" } }]);
  });

  it("skips a block missing an event or data line", () => {
    const { frames } = parseSseFrames("data: {}\n\n");
    expect(frames).toEqual([]);
  });
});

describe("readSseStream", () => {
  function fakeStreamResponse(chunks: string[], opts: { ok?: boolean; status?: number } = {}) {
    const encoder = new TextEncoder();
    let i = 0;
    const body = new ReadableStream<Uint8Array>({
      pull(controller) {
        if (i < chunks.length) {
          controller.enqueue(encoder.encode(chunks[i++]));
        } else {
          controller.close();
        }
      },
    });
    return new Response(body, { status: opts.status ?? 200 });
  }

  it("dispatches frames split across multiple chunks", async () => {
    const res = fakeStreamResponse([
      'event: token\ndata: {"text":"he',
      'llo"}\n\n',
      'event: done\ndata: {}\n\n',
    ]);
    const events: Array<[string, unknown]> = [];
    await readSseStream(res, { onEvent: (e, d) => events.push([e, d]) });
    expect(events).toEqual([
      ["token", { text: "hello" }],
      ["done", {}],
    ]);
  });

  it("reports an error for a non-ok response with a JSON error body", async () => {
    const res = new Response(JSON.stringify({ error: { message: "boom" } }), { status: 500 });
    let message = "";
    await readSseStream(res, { onEvent: () => {}, onError: (m) => (message = m) });
    expect(message).toBe("boom");
  });
});
