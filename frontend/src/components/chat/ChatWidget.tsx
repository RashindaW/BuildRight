import { useRef, useState } from "react";
import ReactMarkdown from "react-markdown";
import { streamChat } from "../../lib/api/chatStream";
import { queryClient } from "../../lib/queryClient";
import { useUiStore } from "../../store/uiStore";
import type { ChatMessage } from "../../types";

const QUICK = ["Where are cordless drills?", "What's your return policy?", "Do you price match?"];

export function ChatWidget() {
  const { chatOpen, setChatOpen, sessionId, setShortlistedItemIds } = useUiStore();
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const convId = useRef<string | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);

  const scrollDown = () =>
    requestAnimationFrame(() => scrollRef.current?.scrollTo(0, scrollRef.current.scrollHeight));

  async function send(text: string) {
    if (!text.trim() || busy) return;
    setBusy(true);
    setInput("");
    setMessages((m) => [...m, { role: "user", content: text }, { role: "assistant", content: "", pending: true }]);
    scrollDown();

    const setLast = (fn: (c: string) => string) =>
      setMessages((m) => {
        const copy = [...m];
        const last = copy[copy.length - 1];
        copy[copy.length - 1] = { ...last, content: fn(last.content) };
        return copy;
      });

    try {
      await streamChat(text, convId.current, sessionId, (ev) => {
        if (ev.event === "meta") convId.current = (ev.data.conversation_id as string) ?? convId.current;
        else if (ev.event === "delta") setLast((c) => c + (ev.data.text as string));
        else if (ev.event === "validated" && ev.data.replace) setLast(() => ev.data.text as string);
        else if (ev.event === "done") {
          if (ev.data.cart_dirty) queryClient.invalidateQueries({ queryKey: ["cart"] });
          const ids = (ev.data.grounded_item_ids as string[] | undefined) ?? [];
          if (ids.length) setShortlistedItemIds(ids); // surface them on the storefront
        } else if (ev.event === "error") setLast((c) => c || (ev.data.message as string));
        scrollDown();
      });
    } finally {
      setMessages((m) => {
        const copy = [...m];
        copy[copy.length - 1] = { ...copy[copy.length - 1], pending: false };
        return copy;
      });
      setBusy(false);
    }
  }

  if (!chatOpen) {
    return (
      <button
        onClick={() => setChatOpen(true)}
        className="fixed bottom-6 right-6 z-40 rounded-full bg-brand-600 px-5 py-3 text-white shadow-lg hover:bg-brand-700"
      >
        💬 Ask us
      </button>
    );
  }

  return (
    <div className="fixed bottom-6 right-6 z-40 flex h-[32rem] w-96 max-w-[calc(100vw-2rem)] flex-col card">
      <div className="flex items-center justify-between border-b bg-brand-600 px-4 py-3 text-white rounded-t-xl">
        <span className="font-semibold">Store Assistant</span>
        <button onClick={() => setChatOpen(false)} aria-label="Close chat">✕</button>
      </div>

      <div ref={scrollRef} className="flex-1 space-y-3 overflow-y-auto p-4">
        {messages.length === 0 && (
          <div className="text-sm text-gray-500">
            <p className="mb-2">Hi! Ask me about any product, price, or store policy.</p>
            <div className="flex flex-wrap gap-2">
              {QUICK.map((q) => (
                <button key={q} className="rounded-full bg-gray-100 px-3 py-1 text-xs hover:bg-gray-200" onClick={() => send(q)}>
                  {q}
                </button>
              ))}
            </div>
          </div>
        )}
        {messages.map((m, i) => (
          <div key={i} className={m.role === "user" ? "text-right" : "text-left"}>
            <div
              className={`inline-block max-w-[85%] rounded-2xl px-3 py-2 text-sm ${
                m.role === "user" ? "bg-brand-600 text-white" : "bg-gray-100 text-gray-900"
              }`}
            >
              {m.role === "assistant" ? (
                <div className="markdown">
                  <ReactMarkdown>{m.content || (m.pending ? "…" : "")}</ReactMarkdown>
                </div>
              ) : (
                m.content
              )}
            </div>
          </div>
        ))}
      </div>

      <form
        className="flex gap-2 border-t p-3"
        onSubmit={(e) => {
          e.preventDefault();
          send(input);
        }}
      >
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Type your question…"
          className="flex-1 rounded-lg border border-gray-300 px-3 py-2 text-sm"
          aria-label="Chat message"
        />
        <button className="btn-primary" disabled={busy}>
          Send
        </button>
      </form>
    </div>
  );
}
