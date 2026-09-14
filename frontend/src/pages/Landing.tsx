import { Link, useNavigate } from "react-router-dom";
import {
  ArrowRight,
  Bot,
  Building2,
  FileSearch,
  Landmark,
  MessagesSquare,
  Search,
  ShieldCheck,
  Sparkles,
  Upload,
} from "lucide-react";
import { useAuth } from "../context/AuthContext";
import { api } from "../services/api";
import { useQuery } from "@tanstack/react-query";

const POPULAR: Record<string, string[]> = {
  consumer: [
    "How can I check if a product is BIS certified?",
    "What is the ISI mark?",
    "Which products require mandatory BIS certification?",
    "How do I lodge a complaint with BIS?",
  ],
  industry: [
    "What standards and requirements should I check before manufacturing a product?",
    "How can I get BIS certification for my factory?",
    "What documents are required for the licence application?",
    "What is the Scheme of Testing and Inspection (STI)?",
  ],
};

export default function LandingPage() {
  const { user, mode } = useAuth();
  const navigate = useNavigate();

  const recent = useQuery({
    queryKey: ["conversations", ""],
    queryFn: () => api.conversations(),
    enabled: !!user,
  });

  const cards = [
    {
      to: user ? "/chat" : "/login",
      icon: Bot,
      title: "Ask BIS Buddy",
      desc: "Get grounded answers about Indian Standards and BIS processes with citations.",
      accent: "bg-brand-50 text-brand-600",
    },
    {
      to: user ? "/documents" : "/login",
      icon: FileSearch,
      title: "Search Standards",
      desc: "Semantic search across indexed standards, guides and technical documents.",
      accent: "bg-emerald-50 text-emerald-600",
    },
    {
      to: user && user.role === "admin" ? "/admin" : "/login",
      icon: Upload,
      title: "Upload Documents",
      desc: "Admins can add official BIS PDFs; the RAG pipeline indexes them automatically.",
      accent: "bg-amber-50 text-amber-600",
    },
    {
      to: "https://www.bis.gov.in",
      icon: Landmark,
      title: "Explore BIS Services",
      desc: "Open the official Bureau of Indian Standards portal for licences and services.",
      accent: "bg-sky-50 text-sky-600",
      external: true,
    },
  ];

  return (
    <div className="min-h-full bg-gradient-to-b from-brand-900 via-brand-800 to-slate-50">
      {/* Nav */}
      <nav className="mx-auto flex max-w-6xl items-center justify-between px-4 py-5">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-white/10">
            <ShieldCheck className="h-6 w-6 text-saffron" />
          </div>
          <div className="text-white">
            <div className="text-lg font-bold leading-tight">BIS Buddy</div>
            <div className="text-[11px] text-white/60">
              Your AI Assistant for Indian Standards & BIS Services
            </div>
          </div>
        </div>
        <div className="flex items-center gap-2">
          {user ? (
            <button
              onClick={() => navigate("/chat")}
              className="rounded-xl bg-saffron px-4 py-2 text-sm font-semibold text-brand-900 hover:brightness-110"
            >
              Open Assistant
            </button>
          ) : (
            <>
              <Link
                to="/login"
                className="rounded-xl px-4 py-2 text-sm font-medium text-white/80 hover:text-white"
              >
                Login
              </Link>
              <Link
                to="/register"
                className="rounded-xl bg-saffron px-4 py-2 text-sm font-semibold text-brand-900 hover:brightness-110"
              >
                Get Started
              </Link>
            </>
          )}
        </div>
      </nav>

      {/* Hero */}
      <div className="mx-auto max-w-6xl px-4 pb-16 pt-10 text-center text-white">
        <div className="mx-auto mb-4 inline-flex items-center gap-2 rounded-full bg-white/10 px-4 py-1.5 text-xs font-medium">
          <Sparkles className="h-3.5 w-3.5 text-saffron" />
          AI-powered assistant for Indian Standards & BIS Services
        </div>
        <h1 className="mx-auto max-w-3xl text-4xl font-extrabold leading-tight sm:text-5xl">
          Understand Indian Standards with confidence
        </h1>
        <p className="mx-auto mt-4 max-w-2xl text-white/70">
          Ask questions about BIS certification, product standards and compliance procedures.
          Every answer cites the exact document and page it came from.
        </p>
        <div className="mt-8 flex flex-wrap items-center justify-center gap-3">
          <button
            onClick={() => navigate(user ? "/chat" : "/register")}
            className="inline-flex items-center gap-2 rounded-xl bg-saffron px-6 py-3 font-semibold text-brand-900 transition hover:brightness-110"
          >
            Ask BIS Buddy <ArrowRight className="h-4 w-4" />
          </button>
          <Link
            to="/documents"
            className="inline-flex items-center gap-2 rounded-xl border border-white/20 px-6 py-3 font-medium text-white transition hover:bg-white/10"
          >
            <Search className="h-4 w-4" /> Browse Documents
          </Link>
        </div>
      </div>

      {/* Cards */}
      <div className="mx-auto max-w-6xl px-4 pb-16">
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {cards.map((c) =>
            c.external ? (
              <a
                key={c.title}
                href={c.to}
                target="_blank"
                rel="noreferrer"
                className="rounded-2xl border bg-white p-5 shadow-sm transition hover:-translate-y-0.5 hover:shadow-md"
              >
                <CardBody c={c} />
              </a>
            ) : (
              <Link
                key={c.title}
                to={c.to}
                className="rounded-2xl border bg-white p-5 shadow-sm transition hover:-translate-y-0.5 hover:shadow-md"
              >
                <CardBody c={c} />
              </Link>
            )
          )}
        </div>

        {/* Popular questions + recent */}
        <div className="mt-10 grid gap-6 lg:grid-cols-2">
          <div className="rounded-2xl border bg-white p-6">
            <h2 className="mb-1 text-lg font-bold text-slate-900">Popular Questions</h2>
            <p className="mb-4 text-sm text-slate-500">
              {mode === "industry"
                ? "Tuned for Industry / Manufacturer mode"
                : "Tuned for Consumer mode"}
            </p>
            <div className="space-y-2">
              {POPULAR[mode].map((q) => (
                <Link
                  key={q}
                  to={user ? `/chat` : "/login"}
                  state={{ suggested: q }}
                  className="block rounded-xl border bg-slate-50 px-4 py-3 text-sm text-slate-700 transition hover:border-brand-500 hover:bg-brand-50"
                >
                  {q}
                </Link>
              ))}
            </div>
          </div>
          <div className="rounded-2xl border bg-white p-6">
            <div className="mb-4 flex items-center gap-2">
              <MessagesSquare className="h-5 w-5 text-brand-600" />
              <h2 className="text-lg font-bold text-slate-900">Recent Conversations</h2>
            </div>
            {user ? (
              (recent.data ?? []).length > 0 ? (
                <div className="space-y-2">
                  {(recent.data ?? []).slice(0, 5).map((c) => (
                    <Link
                      key={c.id}
                      to={`/chat/${c.id}`}
                      className="block truncate rounded-xl border bg-slate-50 px-4 py-3 text-sm text-slate-700 transition hover:border-brand-500 hover:bg-brand-50"
                    >
                      <span className="mr-2 text-[10px] font-bold uppercase text-slate-400">
                        {c.mode === "industry" ? "IND" : "CON"}
                      </span>
                      {c.title}
                    </Link>
                  ))}
                </div>
              ) : (
                <p className="text-sm text-slate-400">
                  No conversations yet — start your first chat!
                </p>
              )
            ) : (
              <p className="text-sm text-slate-400">Login to see your conversation history.</p>
            )}
          </div>
        </div>

        {/* How it works */}
        <div className="mt-10 rounded-2xl border bg-white p-6">
          <h2 className="mb-4 text-lg font-bold text-slate-900">How BIS Buddy works</h2>
          <div className="grid gap-4 text-sm text-slate-600 sm:grid-cols-4">
            {[
              ["1. Ingest", "Official BIS PDFs are parsed, cleaned and split into sections."],
              ["2. Embed", "Each chunk is embedded and stored in the vector database."],
              ["3. Retrieve", "Your question is matched to the most relevant chunks and reranked."],
              ["4. Answer", "Gemini writes a grounded answer with page-level citations."],
            ].map(([t, d]) => (
              <div key={t} className="rounded-xl bg-slate-50 p-4">
                <div className="mb-1 font-bold text-brand-700">{t}</div>
                {d}
              </div>
            ))}
          </div>
          <p className="mt-4 rounded-xl bg-amber-50 px-4 py-3 text-xs text-amber-800">
            Note: this deployment currently contains <b>SAMPLE DATA</b> documents for
            demonstration. They are not official BIS documents. Admins can upload official BIS
            PDFs with their source URLs for production use.
          </p>
        </div>
      </div>
    </div>
  );
}

function CardBody({ c }: { c: any }) {
  return (
    <>
      <div className={`mb-3 inline-flex h-11 w-11 items-center justify-center rounded-xl ${c.accent}`}>
        <c.icon className="h-5 w-5" />
      </div>
      <div className="font-bold text-slate-900">{c.title}</div>
      <div className="mt-1 text-sm text-slate-500">{c.desc}</div>
    </>
  );
}
