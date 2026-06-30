import { useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import ReactMarkdown from "react-markdown";
import { Bot, Brain, Image as ImageIcon, Mic, Send, ShoppingBag, Square, Star, X } from "lucide-react";
import { streamChat } from "../../lib/api/chatStream";
import { chatApi, mediaApi, menuApi } from "../../lib/api/endpoints";
import { ApiError } from "../../lib/api/client";
import { queryClient } from "../../lib/queryClient";
import { useUiStore } from "../../store/uiStore";
import { useAuth } from "../../context/AuthProvider";
import { ProductCardInline } from "./ProductCardInline";
import type { ChatMessage } from "../../types";

const QUICK = ["Where are cordless drills?", "Do you sell a laser level?", "What's your return policy?"];

export function ChatWidget() {
  const { chatOpen, setChatOpen, sessionId, setShortlistedItemIds } = useUiStore();
  const shortlistedItemIds = useUiStore((s) => s.shortlistedItemIds);
  const setShowOnlyShortlist = useUiStore((s) => s.setShowOnlyShortlist);
  const { user } = useAuth();
  const navigate = useNavigate();
  const [showMemory, setShowMemory] = useState(false);
  const memory = useQuery({
    queryKey: ["chat-memory"],
    queryFn: chatApi.memory,
    enabled: chatOpen && !!user,
  });
  const memCount =
    Object.keys(memory.data?.preferences ?? {}).length + (memory.data?.recent_summaries.length ?? 0);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [recording, setRecording] = useState(false);
  const [transcribing, setTranscribing] = useState(false);
  const [imgBusy, setImgBusy] = useState(false);
  const [voiceErr, setVoiceErr] = useState<string | null>(null);
  const [askRating, setAskRating] = useState(false);
  const [rated, setRated] = useState<number | null>(null);
  const recorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const fileRef = useRef<HTMLInputElement>(null);
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
          if (ids.length) {
            setShortlistedItemIds(ids); // also surface them on the storefront
            // Hydrate the grounded products into interactive cards inside this reply.
            menuApi
              .byIds(ids)
              .then((items) => {
                if (!items.length) return;
                setMessages((m) => {
                  const copy = [...m];
                  for (let j = copy.length - 1; j >= 0; j--) {
                    if (copy[j].role === "assistant") {
                      copy[j] = { ...copy[j], cards: items.slice(0, 4) };
                      break;
                    }
                  }
                  return copy;
                });
                scrollDown();
              })
              .catch(() => {});
          }
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
      if (convId.current && rated === null) setAskRating(true); // invite a CSAT rating
      if (user) queryClient.invalidateQueries({ queryKey: ["chat-memory"] }); // refresh remembered prefs
    }
  }

  async function submitRating(n: number) {
    if (!convId.current) return;
    setRated(n);
    setAskRating(false);
    try {
      await chatApi.feedback(convId.current, n);
    } catch {
      /* non-blocking */
    }
  }

  async function startRecording() {
    setVoiceErr(null);
    if (!navigator.mediaDevices?.getUserMedia || typeof MediaRecorder === "undefined") {
      setVoiceErr("Voice isn't supported in this browser.");
      return;
    }
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const rec = new MediaRecorder(stream);
      chunksRef.current = [];
      rec.ondataavailable = (e) => e.data.size && chunksRef.current.push(e.data);
      rec.onstop = async () => {
        stream.getTracks().forEach((t) => t.stop());
        const blob = new Blob(chunksRef.current, { type: rec.mimeType || "audio/webm" });
        if (!blob.size) return;
        setTranscribing(true);
        try {
          const { text } = await mediaApi.transcribe(blob);
          if (text.trim()) await send(text.trim());
          else setVoiceErr("Didn't catch that — try again.");
        } catch (e) {
          setVoiceErr(
            e instanceof ApiError && e.code === "stt_not_configured"
              ? "Voice transcription isn't configured."
              : "Couldn't transcribe that. Please try again.",
          );
        } finally {
          setTranscribing(false);
        }
      };
      recorderRef.current = rec;
      rec.start();
      setRecording(true);
    } catch {
      setVoiceErr("Microphone access was blocked.");
    }
  }

  function stopRecording() {
    recorderRef.current?.stop();
    setRecording(false);
  }

  async function handleImage(file: File) {
    setVoiceErr(null);
    if (!file.type.startsWith("image/")) {
      setVoiceErr("Please choose an image file.");
      return;
    }
    setImgBusy(true);
    setMessages((m) => [
      ...m,
      { role: "user", content: `Sent a photo (${file.name})` },
      { role: "assistant", content: "", pending: true },
    ]);
    scrollDown();
    try {
      const { query, results, note } = await mediaApi.findByImage(file);
      const text =
        results.length > 0
          ? `I think that's a **${query}**. Here's what we carry:\n\n${results
              .slice(0, 8)
              .map((r) => `- ${r.name} — $${(r.price_cents / 100).toFixed(2)}`)
              .join("\n")}`
          : note || "I couldn't identify that item from the photo. Try a clearer, closer shot.";
      setMessages((m) => {
        const copy = [...m];
        copy[copy.length - 1] = { role: "assistant", content: text, pending: false };
        return copy;
      });
      if (results.length) setShortlistedItemIds(results.map((r) => r.slug));
    } catch (e) {
      const msg =
        e instanceof ApiError && e.code === "invalid_image"
          ? "That image couldn't be read."
          : "Sorry, image search failed. Please try again.";
      setMessages((m) => {
        const copy = [...m];
        copy[copy.length - 1] = { role: "assistant", content: msg, pending: false };
        return copy;
      });
    } finally {
      setImgBusy(false);
      if (fileRef.current) fileRef.current.value = "";
    }
  }

  function showShortlistOnSite() {
    setShowOnlyShortlist(true);
    setChatOpen(false);
    navigate("/");
  }

  if (!chatOpen) {
    return (
      <button
        onClick={() => setChatOpen(true)}
        className="fixed bottom-6 right-6 z-40 inline-flex items-center gap-2 rounded-full bg-brand-600 px-5 py-3 font-semibold text-white shadow-pop transition hover:bg-brand-700 active:scale-95"
      >
        <Bot size={18} /> Ask us
      </button>
    );
  }

  return (
    <div className="fixed bottom-6 right-6 z-40 flex h-[32rem] w-96 max-w-[calc(100vw-2rem)] animate-fade-in-up flex-col overflow-hidden rounded-xl2 border border-gray-200 bg-white shadow-pop">
      <div className="flex items-center justify-between border-b bg-brand-600 px-4 py-3 text-white">
        <span className="flex items-center gap-2 font-semibold">
          <Bot size={18} /> BuildRight AI assistant
        </span>
        <div className="flex items-center gap-1">
          {user && memCount > 0 && (
            <button
              onClick={() => setShowMemory((v) => !v)}
              className="inline-flex items-center gap-1 rounded-md bg-white/15 px-2 py-1 text-xs hover:bg-white/25"
              title="What we remember about you"
            >
              <Brain size={13} /> Memory
            </button>
          )}
          <button
            onClick={() => setChatOpen(false)}
            aria-label="Close chat"
            className="grid h-7 w-7 place-items-center rounded-md hover:bg-white/15"
          >
            <X size={16} />
          </button>
        </div>
      </div>

      {user && showMemory && (
        <div className="border-b bg-brand-50 px-4 py-2 text-xs text-gray-700">
          <div className="mb-1 font-medium text-brand-800">What we remember</div>
          {memCount === 0 ? (
            <p className="text-gray-500">Nothing yet — tell me your preferred brand or what you're building.</p>
          ) : (
            <>
              {Object.entries(memory.data?.preferences ?? {}).length > 0 && (
                <div className="mb-1 flex flex-wrap gap-1">
                  {Object.entries(memory.data!.preferences).map(([k, v]) => (
                    <span key={k} className="badge bg-white text-brand-700">{k.replace(/_/g, " ")}: {v}</span>
                  ))}
                </div>
              )}
              {(memory.data?.recent_summaries ?? []).map((s, i) => (
                <div key={i} className="text-gray-600">• {s}</div>
              ))}
            </>
          )}
        </div>
      )}

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
            {m.role === "assistant" && m.cards && m.cards.length > 0 && (
              <div className="mt-2 space-y-2">
                {m.cards.map((it) => (
                  <ProductCardInline key={it.id} item={it} onNavigate={() => setChatOpen(false)} />
                ))}
              </div>
            )}
          </div>
        ))}
      </div>

      {rated !== null ? (
        <div className="border-t bg-green-50 px-3 py-1.5 text-center text-xs text-green-700">
          Thanks for rating this chat {"⭐".repeat(rated)} — it helps the team.
        </div>
      ) : askRating ? (
        <div className="flex items-center justify-center gap-2 border-t bg-gray-50 px-3 py-2 text-sm">
          <span className="text-gray-500">How did I do?</span>
          {[1, 2, 3, 4, 5].map((n) => (
            <button
              key={n}
              type="button"
              onClick={() => submitRating(n)}
              className="text-gray-300 transition hover:scale-110 hover:text-amber-400"
              aria-label={`Rate ${n} of 5`}
              title={`${n} / 5`}
            >
              <Star size={18} className="fill-current" strokeWidth={0} />
            </button>
          ))}
        </div>
      ) : null}

      {shortlistedItemIds.length > 0 && (
        <button
          type="button"
          onClick={showShortlistOnSite}
          className="inline-flex w-full items-center justify-center gap-1.5 border-t bg-brand-50 px-3 py-2 text-sm font-medium text-brand-700 hover:bg-brand-100"
        >
          <ShoppingBag size={15} /> Show these {shortlistedItemIds.length} item{shortlistedItemIds.length > 1 ? "s" : ""} on the storefront →
        </button>
      )}
      {voiceErr && (
        <div className="border-t bg-amber-50 px-3 py-1.5 text-xs text-amber-700">{voiceErr}</div>
      )}
      <form
        className="flex gap-2 border-t p-3"
        onSubmit={(e) => {
          e.preventDefault();
          send(input);
        }}
      >
        <input
          ref={fileRef}
          type="file"
          accept="image/*"
          className="hidden"
          onChange={(e) => e.target.files?.[0] && handleImage(e.target.files[0])}
        />
        <button
          type="button"
          onClick={() => fileRef.current?.click()}
          disabled={busy || imgBusy || recording}
          aria-label="Attach a photo to find an item"
          title="Find an item by photo"
          className="grid h-10 w-10 shrink-0 place-items-center rounded-lg bg-gray-100 text-gray-600 hover:bg-gray-200 disabled:opacity-50"
        >
          {imgBusy ? <span className="animate-pulse">…</span> : <ImageIcon size={18} />}
        </button>
        <button
          type="button"
          onClick={recording ? stopRecording : startRecording}
          disabled={busy || transcribing || imgBusy}
          aria-label={recording ? "Stop recording" : "Record a voice message"}
          title={recording ? "Stop recording" : "Speak your question"}
          className={`grid h-10 w-10 shrink-0 place-items-center rounded-lg ${
            recording
              ? "animate-pulse bg-danger text-white"
              : "bg-gray-100 text-gray-600 hover:bg-gray-200"
          }`}
        >
          {transcribing ? <span className="animate-pulse">…</span> : recording ? <Square size={16} /> : <Mic size={18} />}
        </button>
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder={recording ? "Listening…" : transcribing ? "Transcribing…" : "Type your question…"}
          className="input flex-1"
          aria-label="Chat message"
          disabled={recording || transcribing}
        />
        <button className="btn-primary shrink-0 px-3" disabled={busy} aria-label="Send">
          <Send size={16} />
        </button>
      </form>
    </div>
  );
}
