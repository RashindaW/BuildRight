import { useRef, useState } from "react";
import ReactMarkdown from "react-markdown";
import { Send, Sparkles } from "lucide-react";
import { streamChat } from "../../lib/api/chatStream";
import { WorkingDots } from "../ui/WorkingDots";

const SUGGESTIONS = [
  "What are my best-selling products?",
  "How are my margins this period?",
  "How much revenue did the AI assistant drive?",
  "What's my AI cost and guardrail-violation rate?",
];

interface Msg {
  role: "user" | "assistant";
  content: string;
}

/** Manager-facing "ask your data" chat — streams from /admin/chat/stream. */
export function AdminChat() {
  const [messages, setMessages] = useState<Msg[]>([]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [phase, setPhase] = useState<string | null>(null);
  const convId = useRef<string | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);

  const scrollDown = () =>
    requestAnimationFrame(() => scrollRef.current?.scrollTo(0, scrollRef.current.scrollHeight));

  async function send(text: string) {
    if (!text.trim() || busy) return;
    setBusy(true);
    setPhase("Thinking…");
    setInput("");
    setMessages((m) => [...m, { role: "user", content: text }, { role: "assistant", content: "" }]);
    scrollDown();
    const setLast = (fn: (c: string) => string) =>
      setMessages((m) => {
        const copy = [...m];
        const last = copy[copy.length - 1];
        copy[copy.length - 1] = { ...last, content: fn(last.content) };
        return copy;
      });
    try {
      await streamChat(
        text,
        convId.current,
        "admin",
        (ev) => {
          if (ev.event === "meta") convId.current = (ev.data.conversation_id as string) ?? convId.current;
          else if (ev.event === "status") setPhase((ev.data.label as string) ?? null);
          else if (ev.event === "delta") {
            setPhase(null);
            setLast((c) => c + (ev.data.text as string));
          } else if (ev.event === "delta_reset") setLast(() => "");
          else if (ev.event === "validated" && ev.data.replace) setLast(() => ev.data.text as string);
          else if (ev.event === "error") setLast((c) => c || (ev.data.message as string));
          scrollDown();
        },
        undefined,
        "/api/v1/admin/chat/stream",
      );
    } finally {
      setPhase(null);
      setBusy(false);
    }
  }

  return (
    <div className="card mb-6 flex flex-col overflow-hidden">
      <div className="flex items-center gap-2 border-b bg-brand-600 px-4 py-3 text-white">
        <Sparkles size={18} />
        <span className="font-semibold">Ask your data</span>
        <span className="badge bg-white/15 text-white">AI analyst</span>
      </div>
      <div ref={scrollRef} className="max-h-80 min-h-[6rem] flex-1 space-y-3 overflow-y-auto p-4">
        {messages.length === 0 ? (
          <div className="text-sm text-gray-500">
            <p className="mb-2">Ask about sales, margins, inventory, AI-driven revenue, cost, or CSAT.</p>
            <div className="flex flex-wrap gap-2">
              {SUGGESTIONS.map((q) => (
                <button
                  key={q}
                  className="rounded-full bg-gray-100 px-3 py-1 text-xs hover:bg-gray-200"
                  onClick={() => send(q)}
                >
                  {q}
                </button>
              ))}
            </div>
          </div>
        ) : (
          messages.map((mmsg, i) => (
            <div key={i} className={mmsg.role === "user" ? "text-right" : "text-left"}>
              <div
                className={`inline-block max-w-[85%] rounded-2xl px-3 py-2 text-sm ${
                  mmsg.role === "user" ? "bg-brand-600 text-white" : "bg-gray-100 text-gray-900"
                }`}
              >
                {mmsg.role === "assistant" ? (
                  mmsg.content ? (
                    <div className="markdown">
                      <ReactMarkdown>{mmsg.content}</ReactMarkdown>
                    </div>
                  ) : (
                    <WorkingDots label={i === messages.length - 1 ? phase ?? "Thinking…" : "Thinking…"} />
                  )
                ) : (
                  mmsg.content
                )}
              </div>
            </div>
          ))
        )}
      </div>
      <form
        className="flex gap-2 border-t p-3"
        onSubmit={(e) => {
          e.preventDefault();
          send(input);
        }}
      >
        <input
          className="input flex-1"
          placeholder="Ask about your business…"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          disabled={busy}
        />
        <button className="btn-primary shrink-0 px-3" disabled={busy} aria-label="Send">
          <Send size={16} />
        </button>
      </form>
    </div>
  );
}
