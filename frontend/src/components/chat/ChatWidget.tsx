import { useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import ReactMarkdown from "react-markdown";
import { streamChat } from "../../lib/api/chatStream";
import { mediaApi } from "../../lib/api/endpoints";
import { ApiError } from "../../lib/api/client";
import { queryClient } from "../../lib/queryClient";
import { useUiStore } from "../../store/uiStore";
import type { ChatMessage } from "../../types";

const QUICK = ["Where are cordless drills?", "Do you sell a laser level?", "What's your return policy?"];

export function ChatWidget() {
  const { chatOpen, setChatOpen, sessionId, setShortlistedItemIds } = useUiStore();
  const shortlistedItemIds = useUiStore((s) => s.shortlistedItemIds);
  const setShowOnlyShortlist = useUiStore((s) => s.setShowOnlyShortlist);
  const navigate = useNavigate();
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [recording, setRecording] = useState(false);
  const [transcribing, setTranscribing] = useState(false);
  const [imgBusy, setImgBusy] = useState(false);
  const [voiceErr, setVoiceErr] = useState<string | null>(null);
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
      { role: "user", content: `📷 Sent a photo (${file.name})` },
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

      {shortlistedItemIds.length > 0 && (
        <button
          type="button"
          onClick={showShortlistOnSite}
          className="border-t bg-brand-50 px-3 py-2 text-sm font-medium text-brand-700 hover:bg-brand-100"
        >
          🛍️ Show these {shortlistedItemIds.length} item{shortlistedItemIds.length > 1 ? "s" : ""} on the storefront →
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
          className="rounded-lg bg-gray-100 px-3 py-2 text-sm text-gray-700 hover:bg-gray-200 disabled:opacity-50"
        >
          {imgBusy ? "…" : "🖼️"}
        </button>
        <button
          type="button"
          onClick={recording ? stopRecording : startRecording}
          disabled={busy || transcribing || imgBusy}
          aria-label={recording ? "Stop recording" : "Record a voice message"}
          title={recording ? "Stop recording" : "Speak your question"}
          className={`rounded-lg px-3 py-2 text-sm ${
            recording
              ? "animate-pulse bg-red-600 text-white"
              : "bg-gray-100 text-gray-700 hover:bg-gray-200"
          }`}
        >
          {transcribing ? "…" : recording ? "⏹" : "🎤"}
        </button>
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder={recording ? "Listening…" : transcribing ? "Transcribing…" : "Type your question…"}
          className="flex-1 rounded-lg border border-gray-300 px-3 py-2 text-sm"
          aria-label="Chat message"
          disabled={recording || transcribing}
        />
        <button className="btn-primary" disabled={busy}>
          Send
        </button>
      </form>
    </div>
  );
}
