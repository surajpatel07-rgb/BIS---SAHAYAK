import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import {
  AlertTriangle,
  Bot,
  FileText,
  Landmark,
  Mic,
  MicOff,
  RotateCcw,
  Send,
  ThumbsDown,
  ThumbsUp,
  User,
} from "lucide-react";
import { api, streamChat, type Citation } from "../services/api";
import { useAuth } from "../context/AuthContext";

interface UiMessage {
  id: number | string;
  role: "user" | "assistant";
  content: string;
  sources?: Citation[];
  feedback?: 1 | -1 | undefined;
}

const SUGGESTIONS: Record<string, string[]> = {
  consumer: [
    "How can I check if a product is BIS certified?",
    "What is the ISI mark and what does it guarantee?",
    "How do I file a complaint about a certified product?",
    "Which products need mandatory BIS certification?",
  ],
  industry: [
    "What standards and requirements should I check before manufacturing cement?",
    "How can I get BIS certification for my factory?",
    "What documents are required for the BIS licence application?",
    "What is the Scheme of Testing and Inspection?",
  ],
};

/** Renders answer text, converting [n] markers into clickable citation chips. */
function AnswerWithCitations({
  content,
  sources,
  onCitationClick,
}: {
  content: string;
  sources: Citation[];
  onCitationClick: (c: Citation) => void;
}) {
  const parts = useMemo(() => {
    const out: { type: "text" | "cite"; value: string | number }[] = [];
    const re = /\[(\d{1,2})\]/g;
    let last = 0;
    let m: RegExpExecArray | null;
    while ((m = re.exec(content))) {
      if (m.index > last) out.push({ type: "text", value: content.slice(last, m.index) });
      out.push({ type: "cite", value: Number(m[1]) });
      last = m.index + m[0].length;
    }
    if (last < content.length) out.push({ type: "text", value: content.slice(last) });
    return out;
  }, [content]);

  return (
    <div className="space-y-1.5 whitespace-pre-wrap leading-relaxed">
      {parts.map((p, i) =>
        p.type === "text" ? (
          <span key={i}>{p.value}</span>
        ) : (
          (() => {
            const idx = p.value as number;
            const c = sources[idx - 1];
            if (!c) return <span key={i}>[{idx}]</span>;
            return (
              <button
                key={i}
                onClick={() => onCitationClick(c)}
                title={`${c.document_name} — page ${c.page}${c.section ? ` · ${c.section}` : ""}`}
                className="mx-0.5 inline-flex h-5 min-w-5 items-center justify-center rounded-md bg-brand-100 px-1 align-baseline text-[11px] font-bold text-brand-700 hover:bg-brand-500 hover:text-white"
              >
                {idx}
              </button>
            );
          })()
        )
      )}
    </div>
  );
}

function CitationCard({ c }: { c: Citation }) {
  const fileUrl = api.documentFileUrl(c.document_id);
  return (
    <a
      href={`${fileUrl}#page=${c.page}`}
      target="_blank"
      rel="noreferrer"
      className="block rounded-xl border bg-white p-3 transition hover:border-brand-500 hover:shadow-sm"
    >
      <div className="flex items-start gap-2.5">
        <FileText className="mt-0.5 h-4 w-4 shrink-0 text-brand-500" />
        <div className="min-w-0">
          <div className="truncate text-sm font-semibold text-slate-800">
            {c.standard_number || c.document_name}
          </div>
          <div className="truncate text-xs text-slate-500">{c.title || c.document_name}</div>
          <div className="mt-1 flex flex-wrap items-center gap-1.5 text-[11px] text-slate-500">
            <span className="rounded bg-slate-100 px-1.5 py-0.5">Page {c.page}</span>
            {c.section && (
              <span className="max-w-44 truncate rounded bg-slate-100 px-1.5 py-0.5">
                {c.section}
              </span>
            )}
            {c.year && <span className="rounded bg-slate-100 px-1.5 py-0.5">{c.year}</span>}
            <span className="rounded bg-emerald-50 px-1.5 py-0.5 text-emerald-700">
              {(c.relevance_score * 100).toFixed(0)}% match
            </span>
          </div>
        </div>        </div>
      </a>
  );
}

export default function ChatPage() {
  const { conversationId } = useParams();
  const { mode } = useAuth();
  const [messages, setMessages] = useState<UiMessage[]>([]);
  const [input, setInput] = useState("");
  const [streaming, setStreaming] = useState(false);
  const [streamText, setStreamText] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [voiceSupported, setVoiceSupported] = useState(true);
  const [listening, setListening] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);
  const recognitionRef = useRef<any>(null);
  const lastLoadedConv = useRef<number | null>(null);

  // Load conversation history when opening /chat/:id
  useEffect(() => {
    const cid = Number(conversationId) || null;
    if (cid === lastLoadedConv.current) return;
    lastLoadedConv.current = cid;
    if (!cid) {
      setMessages([]);
      return;
    }
    api.conversation(cid).then((d) => {
      setMessages(
        d.messages.map((m) => ({
          id: m.id,
          role: m.role,
          content: m.content,
          sources: m.sources_json?.sources ?? [],
        }))
      );
    });
  }, [conversationId]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, streamText]);

  // Voice input via Web Speech API (graceful fallback)
  useEffect(() => {
    const w = window as any;
    const SR = w.SpeechRecognition || w.webkitSpeechRecognition;
    if (!SR) {
      setVoiceSupported(false);
      return;
    }
    const rec = new SR();
    rec.lang = "en-IN";
    rec.interimResults = false;
    rec.maxAlternatives = 1;
    rec.onresult = (e: any) => {
      const text = Array.from(e.results)
        .map((r: any) => r[0].transcript)
        .join(" ");
      setInput((prev) => (prev ? `${prev} ${text}` : text));
    };
    rec.onend = () => setListening(false);
    rec.onerror = () => setListening(false);
    recognitionRef.current = rec;
    return () => {
      try {
        rec.stop();
      } catch {
        /* noop */
      }
    };
  }, []);

  const toggleVoice = () => {
    const rec = recognitionRef.current;
    if (!rec) return;
    if (listening) {
      rec.stop();
      setListening(false);
    } else {
      rec.start();
      setListening(true);
    }
  };

  const send = useCallback(
    async (text: string) => {
      const trimmed = text.trim();
      if (!trimmed || streaming) return;
      setError(null);
      setInput("");
      setMessages((prev) => [
        ...prev,
        { id: `u-${Date.now()}`, role: "user", content: trimmed },
      ]);
      setStreaming(true);
      setStreamText("");

      let convId = Number(conversationId) || null;
      let acc = "";
      await streamChat(
        { message: trimmed, conversation_id: convId, mode },
        {
          onMeta: (meta) => {
            convId = meta.conversation_id;
          },
          onDelta: (piece) => {
            acc += piece;
            setStreamText(acc);
          },
          onDone: (final) => {
            setStreamText("");
            setStreaming(false);
            setMessages((prev) => [
              ...prev,
              {
                id: final.message_id,
                role: "assistant",
                content: acc,
                sources: final.sources,
              },
            ]);
          },
          onError: (msg) => {
            setError(msg || "The assistant is unavailable. Please try again.");
            setStreaming(false);
          },
        }
      ).catch(() => {
        setError("Network error — is the backend running on port 8000?");
        setStreaming(false);
      });
    },
    [conversationId, mode, streaming]
  );

  const giveFeedback = async (messageId: number | string, rating: 1 | -1) => {
    if (typeof messageId !== "number") return;
    setMessages((prev) =>
      prev.map((m) => (m.id === messageId ? { ...m, feedback: rating } : m))
    );
    try {
      await api.feedback(messageId, rating);
    } catch {
      /* non-fatal */
    }
  };

  const lastAssistant = [...messages].reverse().find((m) => m.role === "assistant");
  const showWelcome = messages.length === 0 && !streaming;

  return (
    <div className="flex h-full flex-col">
      {/* Mode banner */}
      <div className="flex items-center justify-between border-b bg-white px-4 py-2">
        <div className="flex items-center gap-2 text-sm">
          {mode === "industry" ? (
            <>
              <Landmark className="h-4 w-4 text-brand-600" />
              <span className="font-semibold text-brand-800">Industry mode</span>
              <span className="hidden text-slate-500 sm:inline">
                — compliance, procedures & testing guidance
              </span>
            </>
          ) : (
            <>
              <User className="h-4 w-4 text-indiaGreen" />
              <span className="font-semibold text-brand-800">Consumer mode</span>
              <span className="hidden text-slate-500 sm:inline">
                — simple explanations & safety guidance
              </span>
            </>
          )}
        </div>
        <Link
          to="/documents"
          className="text-xs font-medium text-brand-600 hover:text-brand-800"
        >
          Search Documents →
        </Link>
      </div>

      {/* Messages */}
      <div className="thin-scroll flex-1 overflow-y-auto">
        <div className="mx-auto max-w-3xl px-4 py-6">
          {showWelcome && (
            <div className="mb-6 rounded-2xl border bg-white p-6">
              <div className="mb-2 flex items-center gap-3">
                <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-brand-50">
                  <Bot className="h-6 w-6 text-brand-600" />
                </div>
                <div>
                  <h1 className="text-lg font-bold text-slate-900">Hello! I'm BIS Buddy.</h1>
                  <p className="text-sm text-slate-500">
                    I can help you understand Indian Standards, BIS requirements and
                    certification-related information.
                  </p>
                </div>
              </div>
              <div className="mt-4 grid gap-2 sm:grid-cols-2">
                {SUGGESTIONS[mode].map((s) => (
                  <button
                    key={s}
                    onClick={() => send(s)}
                    className="rounded-xl border bg-slate-50 px-3 py-2.5 text-left text-sm text-slate-700 transition hover:border-brand-500 hover:bg-brand-50"
                  >
                    {s}
                  </button>
                ))}
              </div>
              <p className="mt-4 text-xs text-slate-400">
                Answers are grounded in the indexed documents. Every factual claim links to its
                source — click a citation chip to open the document page.
              </p>
            </div>
          )}

          {messages.map((m) => (
            <div key={m.id} className={`mb-4 flex ${m.role === "user" ? "justify-end" : ""}`}>
              <div
                className={`max-w-[92%] rounded-2xl px-4 py-3 text-sm ${
                  m.role === "user"
                    ? "bg-brand-600 text-white"
                    : "border bg-white text-slate-800"
                }`}
              >
                {m.role === "assistant" ? (
                  <AnswerWithCitations
                    content={m.content}
                    sources={m.sources ?? []}
                    onCitationClick={() => {
                      /* citations open via cards below + chips link out */
                    }}
                  />
                ) : (
                  m.content
                )}
                {m.role === "assistant" && (m.sources?.length ?? 0) > 0 && (
                  <div className="mt-3 border-t pt-3">
                    <div className="mb-1.5 text-[11px] font-semibold uppercase tracking-wide text-slate-400">
                      Sources
                    </div>
                    <div className="grid gap-2 sm:grid-cols-2">
                      {m.sources!.map((c, i) => (
                        <CitationCard key={i} c={c} />
                      ))}
                    </div>
                  </div>
                )}
                {m.role === "assistant" && typeof m.id === "number" && (
                  <div className="mt-2 flex gap-1">
                    <button
                      onClick={() => giveFeedback(m.id as number, 1)}
                      className={`rounded-lg p-1.5 transition ${
                        m.feedback === 1
                          ? "bg-emerald-50 text-emerald-600"
                          : "text-slate-300 hover:bg-slate-50 hover:text-slate-500"
                      }`}
                      title="Helpful"
                    >
                      <ThumbsUp className="h-3.5 w-3.5" />
                    </button>
                    <button
                      onClick={() => giveFeedback(m.id as number, -1)}
                      className={`rounded-lg p-1.5 transition ${
                        m.feedback === -1
                          ? "bg-red-50 text-red-500"
                          : "text-slate-300 hover:bg-slate-50 hover:text-slate-500"
                      }`}
                      title="Not helpful"
                    >
                      <ThumbsDown className="h-3.5 w-3.5" />
                    </button>
                  </div>
                )}
              </div>
            </div>
          ))}

          {streaming && (
            <div className="mb-4 flex justify-start">
              <div className="max-w-[92%] rounded-2xl border bg-white px-4 py-3 text-sm">
                {streamText ? (
                  <AnswerWithCitations
                    content={streamText}
                    sources={lastAssistant?.sources ?? []}
                    onCitationClick={() => {}}
                  />
                ) : (
                  <div className="flex items-center gap-2 text-slate-400">
                    <Bot className="h-4 w-4 animate-pulse" />
                    BIS Buddy is thinking…
                  </div>
                )}
              </div>
            </div>
          )}

          {error && (
            <div className="mb-4 flex items-start gap-2 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
              <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
              <div>
                {error}
                <button
                  onClick={() => window.location.reload()}
                  className="ml-2 inline-flex items-center gap-1 font-semibold underline"
                >
                  <RotateCcw className="h-3 w-3" /> Retry
                </button>
              </div>
            </div>
          )}
          <div ref={bottomRef} />
        </div>
      </div>

      {/* Input */}
      <div className="border-t bg-white px-4 py-3">
        <div className="mx-auto flex max-w-3xl items-end gap-2">
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                send(input);
              }
            }}
            rows={1}
            placeholder={
              mode === "industry"
                ? "Ask about standards, compliance, certification…"
                : "Ask about product standards, ISI mark, complaints…"
            }
            className="thin-scroll max-h-36 flex-1 resize-none rounded-xl border px-4 py-3 text-sm outline-none transition focus:border-brand-500 focus:ring-2 focus:ring-brand-100"
          />
          {voiceSupported ? (
            <button
              onClick={toggleVoice}
              title={listening ? "Stop listening" : "Speak your question"}
              className={`rounded-xl p-3 transition ${
                listening
                  ? "animate-pulse bg-red-100 text-red-600"
                  : "bg-slate-100 text-slate-600 hover:bg-slate-200"
              }`}
            >
              {listening ? <MicOff className="h-5 w-5" /> : <Mic className="h-5 w-5" />}
            </button>
          ) : (
            <div
              title="Voice input requires a browser with the Web Speech API (e.g. Chrome or Edge)."
              className="cursor-not-allowed rounded-xl bg-slate-100 p-3 text-slate-300"
            >
              <MicOff className="h-5 w-5" />
            </div>
          )}
          <button
            onClick={() => send(input)}
            disabled={!input.trim() || streaming}
            className="rounded-xl bg-brand-600 p-3 text-white transition hover:bg-brand-700 disabled:cursor-not-allowed disabled:opacity-40"
            title="Send"
          >
            <Send className="h-5 w-5" />
          </button>
        </div>
        <p className="mx-auto mt-1.5 max-w-3xl text-center text-[11px] text-slate-400">
          BIS Buddy answers from indexed documents with citations. Verify critical compliance
          decisions against the official BIS portal.
        </p>
      </div>
    </div>
  );
}
