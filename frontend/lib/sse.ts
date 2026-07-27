/**
 * SSE frame parsing, in one place.
 *
 * This logic was copy-pasted into four call sites (the Dashboard's upload and
 * summary readers, ChatStream, MasterclassStudio). The boundary handling is
 * subtle enough — split on the blank-line separator, keep the trailing
 * fragment in the buffer because a chunk can end mid-frame — that four
 * independent copies is four chances to get it wrong.
 */

export type SseFrame = { event: string; data: unknown };

export type SseHandlers = {
  onEvent: (event: string, data: never) => void;
  /** Called if the response is not ok, or the stream breaks mid-flight. */
  onError?: (message: string) => void;
  signal?: AbortSignal;
};

/** Split a buffer into complete frames, returning the unparsed remainder. */
export function parseSseFrames(buffer: string): { frames: SseFrame[]; rest: string } {
  const blocks = buffer.split("\n\n");
  // The final element is either "" (buffer ended on a separator) or a partial
  // frame; either way it must stay in the buffer.
  const rest = blocks.pop() ?? "";
  const frames: SseFrame[] = [];

  for (const block of blocks) {
    const lines = block.split("\n");
    const eventLine = lines.find((l) => l.startsWith("event:"));
    const dataLine = lines.find((l) => l.startsWith("data:"));
    if (!eventLine || !dataLine) continue;
    try {
      frames.push({
        event: eventLine.slice("event:".length).trim(),
        data: JSON.parse(dataLine.slice("data:".length).trim()),
      });
    } catch {
      // A frame we cannot parse is skipped rather than killing the stream.
    }
  }
  return { frames, rest };
}

/** Read an SSE response to completion, dispatching each frame. */
export async function readSseStream(res: Response, handlers: SseHandlers): Promise<void> {
  if (!res.ok || !res.body) {
    // An upstream failure arrives as JSON, not SSE — surface its message.
    let message = `Request failed (HTTP ${res.status}).`;
    try {
      const body = await res.json();
      message = body?.error?.message ?? message;
    } catch {
      /* body was not JSON; keep the status-based message */
    }
    handlers.onError?.(message);
    return;
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const { frames, rest } = parseSseFrames(buffer);
      buffer = rest;
      for (const frame of frames) {
        handlers.onEvent(frame.event, frame.data as never);
      }
    }
  } catch (err) {
    // Aborting is how a caller cancels; it is not a failure.
    if ((err as Error)?.name === "AbortError") return;
    handlers.onError?.("The stream was interrupted before it finished.");
  } finally {
    reader.releaseLock?.();
  }
}
