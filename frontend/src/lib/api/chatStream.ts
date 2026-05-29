import { ensureCsrf } from "./client";

export interface ChatEvent {
  event: string;
  data: Record<string, unknown>;
}

function getCookie(name: string): string | null {
  const m = document.cookie.match(new RegExp("(^| )" + name + "=([^;]+)"));
  return m ? decodeURIComponent(m[2]) : null;
}

/**
 * POST a chat message and consume the SSE stream via fetch + ReadableStream.
 * Calls onEvent for each parsed SSE event. Returns when the stream ends.
 */
export async function streamChat(
  message: string,
  conversationId: string | null,
  sessionId: string,
  onEvent: (e: ChatEvent) => void,
  signal?: AbortSignal,
): Promise<void> {
  await ensureCsrf();
  const res = await fetch("/api/v1/chat/stream", {
    method: "POST",
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
      "x-csrf-token": getCookie("csrf_token") ?? "",
      "x-session-id": sessionId,
    },
    body: JSON.stringify({ message, conversation_id: conversationId }),
    signal,
  });

  if (!res.ok || !res.body) {
    onEvent({ event: "error", data: { message: "Chat is unavailable right now." } });
    return;
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const chunks = buffer.split("\n\n");
    buffer = chunks.pop() ?? "";
    for (const chunk of chunks) {
      const lines = chunk.split("\n");
      let event = "message";
      let dataStr = "";
      for (const line of lines) {
        if (line.startsWith("event:")) event = line.slice(6).trim();
        else if (line.startsWith("data:")) dataStr += line.slice(5).trim();
      }
      if (dataStr) {
        try {
          onEvent({ event, data: JSON.parse(dataStr) });
        } catch {
          /* ignore malformed */
        }
      }
    }
  }
}
