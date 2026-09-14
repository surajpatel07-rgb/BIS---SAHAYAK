import { useRef, useState } from "react";
import { Link } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  AlertTriangle,
  CheckCircle2,
  Database,
  FileStack,
  FileText,
  Layers,
  Loader2,
  RefreshCw,
  Search,
  Trash2,
  Upload,
  XCircle,
} from "lucide-react";
import { api, type DocumentOut } from "../services/api";
import { StatusBadge } from "./Documents";

const STATUS_STEPS = ["uploaded", "extracting", "chunking", "embedding", "indexed"];

function UploadForm() {
  const queryClient = useQueryClient();
  const fileRef = useRef<HTMLInputElement>(null);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<{ ok: boolean; text: string } | null>(null);
  const categories = useQuery({ queryKey: ["categories"], queryFn: api.categories });
  const [meta, setMeta] = useState({
    title: "",
    standard_number: "",
    year: "",
    document_type: "standard",
    category: "general_bis",
    subcategory: "",
    product_name: "",
    language: "en",
    description: "",
    source_url: "",
    source_name: "",
    source_type: "demo",
  });

  const upload = async (file: File) => {
    setBusy(true);
    setMessage(null);
    const form = new FormData();
    form.append("file", file);
    Object.entries(meta).forEach(([k, v]) => {
      if (v !== "") form.append(k, v);
    });
    try {
      const res = await api.uploadDocument(form);
      setMessage({
        ok: res.status === "indexed",
        text:
          res.status === "indexed"
            ? `"${res.name}" indexed successfully with ${res.chunk_count} chunks.`
            : `Upload stored, but ingestion finished with status "${res.status}".`,
      });
      queryClient.invalidateQueries({ queryKey: ["documents"] });
      queryClient.invalidateQueries({ queryKey: ["adminStats"] });
    } catch (err: any) {
      setMessage({ ok: false, text: err?.message ?? "Upload failed" });
    } finally {
      setBusy(false);
      if (fileRef.current) fileRef.current.value = "";
    }
  };

  return (
    <div className="rounded-2xl border bg-white p-5">
      <h2 className="mb-1 flex items-center gap-2 font-bold text-slate-900">
        <Upload className="h-5 w-5 text-brand-600" /> Upload document
      </h2>
      <p className="mb-4 text-xs text-slate-500">
        PDF up to 25 MB. The ingestion pipeline extracts text, chunks it, generates embeddings
        and indexes it for retrieval.
      </p>

      <input
        ref={fileRef}
        type="file"
        accept="application/pdf,.pdf"
        onChange={(e) => {
          const f = e.target.files?.[0];
          if (f) upload(f);
        }}
        className="mb-3 w-full cursor-pointer rounded-xl border border-dashed px-3 py-6 text-sm text-slate-500 hover:border-brand-500"
      />

      <div className="grid gap-3 sm:grid-cols-2">
        <input
          value={meta.title}
          onChange={(e) => setMeta({ ...meta, title: e.target.value })}
          placeholder="Title (optional)"
          className="rounded-xl border px-3 py-2 text-sm outline-none focus:border-brand-500"
        />
        <input
          value={meta.standard_number}
          onChange={(e) => setMeta({ ...meta, standard_number: e.target.value })}
          placeholder="Standard number, e.g. IS 1234:2020"
          className="rounded-xl border px-3 py-2 text-sm outline-none focus:border-brand-500"
        />
        <input
          value={meta.year}
          onChange={(e) => setMeta({ ...meta, year: e.target.value })}
          placeholder="Year"
          type="number"
          className="rounded-xl border px-3 py-2 text-sm outline-none focus:border-brand-500"
        />
        <select
          value={meta.document_type}
          onChange={(e) => setMeta({ ...meta, document_type: e.target.value })}
          className="rounded-xl border px-3 py-2 text-sm outline-none focus:border-brand-500"
        >
          <option value="standard">Standard</option>
          <option value="guide">Guide</option>
          <option value="circular">Circular</option>
          <option value="order">Order / QCO</option>
          <option value="other">Other</option>
        </select>
        <select
          value={meta.category}
          onChange={(e) => setMeta({ ...meta, category: e.target.value })}
          className="rounded-xl border px-3 py-2 text-sm outline-none focus:border-brand-500"
        >
          {(categories.data ?? []).map((c) => (
            <option key={c.key} value={c.key}>
              {c.emoji} {c.label}
            </option>
          ))}
        </select>
        <input
          value={meta.subcategory}
          onChange={(e) => setMeta({ ...meta, subcategory: e.target.value })}
          placeholder="Subcategory (e.g. Water, Cables)"
          className="rounded-xl border px-3 py-2 text-sm outline-none focus:border-brand-500"
        />
        <input
          value={meta.product_name}
          onChange={(e) => setMeta({ ...meta, product_name: e.target.value })}
          placeholder="Product name (e.g. Packaged Drinking Water)"
          className="rounded-xl border px-3 py-2 text-sm outline-none focus:border-brand-500"
        />
        <select
          value={meta.language}
          onChange={(e) => setMeta({ ...meta, language: e.target.value })}
          className="rounded-xl border px-3 py-2 text-sm outline-none focus:border-brand-500"
        >
          <option value="en">English</option>
          <option value="hi">Hindi</option>
        </select>
        <select
          value={meta.source_type}
          onChange={(e) => setMeta({ ...meta, source_type: e.target.value })}
          className="rounded-xl border px-3 py-2 text-sm outline-none focus:border-brand-500"
        >
          <option value="official_bis">Official BIS source</option>
          <option value="government">Government of India</option>
          <option value="official">Other official</option>
          <option value="demo">Demo / sample data</option>
        </select>
        <input
          value={meta.source_name}
          onChange={(e) => setMeta({ ...meta, source_name: e.target.value })}
          placeholder="Source name (e.g. Bureau of Indian Standards)"
          className="rounded-xl border px-3 py-2 text-sm outline-none focus:border-brand-500"
        />
        <input
          value={meta.source_url}
          onChange={(e) => setMeta({ ...meta, source_url: e.target.value })}
          placeholder="Official source URL (optional)"
          className="rounded-xl border px-3 py-2 text-sm outline-none focus:border-brand-500"
        />
        <textarea
          value={meta.description}
          onChange={(e) => setMeta({ ...meta, description: e.target.value })}
          placeholder="Description (optional)"
          rows={2}
          className="rounded-xl border px-3 py-2 text-sm outline-none focus:border-brand-500 sm:col-span-2"
        />
      </div>

      {busy && (
        <div className="mt-3 flex items-center gap-2 rounded-xl bg-amber-50 px-3 py-2 text-sm text-amber-800">
          <Loader2 className="h-4 w-4 animate-spin" /> Processing: extracting → chunking →
          embedding → indexing…
        </div>
      )}
      {message && (
        <div
          className={`mt-3 flex items-start gap-2 rounded-xl px-3 py-2 text-sm ${
            message.ok ? "bg-emerald-50 text-emerald-800" : "bg-red-50 text-red-700"
          }`}
        >
          {message.ok ? (
            <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0" />
          ) : (
            <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
          )}
          {message.text}
        </div>
      )}
    </div>
  );
}

function DocumentRow({ d }: { d: DocumentOut }) {
  const queryClient = useQueryClient();
  const del = useMutation({
    mutationFn: () => api.deleteDocument(d.id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["documents"] }),
  });
  const reindex = useMutation({
    mutationFn: () => api.reindexDocument(d.id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["documents"] });
      queryClient.invalidateQueries({ queryKey: ["adminStats"] });
    },
  });

  return (
    <tr className="border-b text-sm last:border-0 hover:bg-slate-50">
      <td className="max-w-52 truncate px-3 py-2.5 font-medium text-slate-800" title={d.name}>
        <Link to={`/documents/${d.id}`} className="hover:text-brand-600">
          {d.title || d.name}
        </Link>
      </td>
      <td className="px-3 py-2.5 text-slate-600">{d.standard_number || "—"}</td>
      <td className="px-3 py-2.5">
        <StatusBadge status={d.status} />
        {d.status === "failed" && d.error_message && (
          <div className="mt-1 max-w-64 truncate text-[11px] text-red-500" title={d.error_message}>
            {d.error_message}
          </div>
        )}
      </td>
      <td className="px-3 py-2.5 text-slate-600">{d.chunk_count ?? 0}</td>
      <td className="px-3 py-2.5 text-slate-600">{d.page_count}</td>
      <td className="px-3 py-2.5">
        <div className="flex gap-1">
          <button
            onClick={() => reindex.mutate()}
            disabled={reindex.isPending}
            title="Re-index"
            className="rounded-lg p-1.5 text-slate-400 transition hover:bg-brand-50 hover:text-brand-600"
          >
            <RefreshCw className={`h-4 w-4 ${reindex.isPending ? "animate-spin" : ""}`} />
          </button>
          <button
            onClick={() => del.mutate()}
            disabled={del.isPending}
            title="Delete"
            className="rounded-lg p-1.5 text-slate-400 transition hover:bg-red-50 hover:text-red-600"
          >
            <Trash2 className="h-4 w-4" />
          </button>
        </div>
      </td>
    </tr>
  );
}

function KnowledgeStatsPanel() {
  const kb = useQuery({ queryKey: ["knowledgeStats"], queryFn: api.knowledgeStats });
  return (
    <div className="rounded-2xl border bg-white p-5">
      <h2 className="mb-1 font-bold text-slate-900">Knowledge base by category</h2>
      <p className="mb-3 text-xs text-slate-500">
        Live database counts — documents, indexed and chunks per knowledge category.
      </p>
      <div className="overflow-x-auto">
        <table className="w-full text-left text-sm">
          <thead>
            <tr className="border-b text-xs uppercase tracking-wide text-slate-500">
              <th className="py-2 font-semibold">Category</th>
              <th className="py-2 font-semibold">Docs</th>
              <th className="py-2 font-semibold">Indexed</th>
              <th className="py-2 font-semibold">Chunks</th>
              <th className="py-2 font-semibold">Failed</th>
            </tr>
          </thead>
          <tbody>
            {(kb.data?.categories ?? []).map((c) => (
              <tr key={c.key} className="border-b last:border-0">
                <td className="py-2 font-medium text-slate-700">
                  {c.emoji} {c.label}
                </td>
                <td className="py-2 text-slate-600">{c.documents}</td>
                <td className="py-2 text-emerald-600">{c.indexed}</td>
                <td className="py-2 text-slate-600">{c.chunks}</td>
                <td className={`py-2 ${c.failed ? "text-red-500" : "text-slate-400"}`}>
                  {c.failed}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="mt-3 text-xs text-slate-400">
        Registry: {kb.data?.total_products ?? 0} products · {kb.data?.total_standards ?? 0} standards
        {kb.data?.last_updated
          ? ` · last updated ${new Date(kb.data.last_updated).toLocaleString()}`
          : ""}
      </div>
    </div>
  );
}

function RagDebugPanel() {
  const [q, setQ] = useState("");
  const [submitted, setSubmitted] = useState("");
  const trace = useQuery({
    queryKey: ["ragDebug", submitted],
    queryFn: () => api.ragDebug(submitted),
    enabled: !!submitted,
  });

  return (
    <div className="rounded-2xl border bg-white p-5">
      <h2 className="mb-1 font-bold text-slate-900">RAG debugging panel</h2>
      <p className="mb-3 text-xs text-slate-500">
        Admin-only: inspect how a query is classified and which chunks the retriever picked.
      </p>
      <div className="flex gap-2">
        <input
          value={q}
          onChange={(e) => setQ(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter") setSubmitted(q.trim());
          }}
          placeholder='Try: "What is HUID?" or "pressure cooker"'
          className="w-full rounded-xl border px-3 py-2 text-sm outline-none focus:border-brand-500"
        />
        <button
          onClick={() => setSubmitted(q.trim())}
          disabled={!q.trim()}
          className="rounded-xl bg-brand-600 px-4 py-2 text-sm font-semibold text-white hover:bg-brand-700 disabled:opacity-40"
        >
          Trace
        </button>
      </div>

      {trace.isFetching && (
        <div className="mt-3 flex items-center gap-2 text-sm text-slate-500">
          <Loader2 className="h-4 w-4 animate-spin" /> Running retrieval trace…
        </div>
      )}

      {trace.data && (
        <div className="mt-4 space-y-3 text-sm">
          <div className="grid gap-2 rounded-xl bg-slate-50 p-3 sm:grid-cols-2">
            <div>
              <span className="text-xs uppercase text-slate-400">Detected category</span>
              <div className="font-semibold text-slate-700">
                {trace.data.detected_category} ({trace.data.category_confidence})
              </div>
            </div>
            <div>
              <span className="text-xs uppercase text-slate-400">Language / product / standard</span>
              <div className="font-semibold text-slate-700">
                {trace.data.language} · {trace.data.matched_product || "—"} ·{" "}
                {trace.data.detected_standard || "—"}
              </div>
            </div>
            <div className="sm:col-span-2">
              <span className="text-xs uppercase text-slate-400">Matched keywords</span>
              <div className="mt-1 flex flex-wrap gap-1">
                {trace.data.matched_keywords.map((k) => (
                  <span
                    key={k}
                    className="rounded bg-white px-1.5 py-0.5 text-xs text-slate-600 ring-1 ring-slate-200"
                  >
                    {k}
                  </span>
                ))}
              </div>
            </div>
          </div>

          <div>
            <div className="mb-1 text-xs font-semibold uppercase text-slate-400">
              Candidates before rerank ({trace.data.candidates_before_rerank.length})
            </div>
            <div className="max-h-40 space-y-1 overflow-y-auto">
              {trace.data.candidates_before_rerank.map((c, i) => (
                <div
                  key={i}
                  className="flex items-center justify-between gap-2 rounded bg-slate-50 px-2 py-1 text-xs text-slate-600"
                >
                  <span className="truncate">
                    {c.standard_number || c.document_name} · p{c.page} · {c.category} ·{" "}
                    {c.source_type}
                  </span>
                  <span className="shrink-0 font-mono text-emerald-600">
                    {c.vector_score.toFixed(3)}
                  </span>
                </div>
              ))}
            </div>
          </div>

          <div>
            <div className="mb-1 text-xs font-semibold uppercase text-slate-400">
              Selected chunks after rerank ({trace.data.selected_chunks.length})
            </div>
            <div className="space-y-1">
              {trace.data.selected_chunks.map((c, i) => (
                <div
                  key={i}
                  className="rounded bg-brand-50 px-2 py-1 text-xs text-slate-700"
                >
                  [{i + 1}] {c.standard_number || c.document_name} · p{c.page}
                  {c.section ? ` · ${c.section}` : ""} · {c.category} —{" "}
                  <span className="font-mono text-brand-700">{c.final_score.toFixed(3)}</span>
                </div>
              ))}
            </div>
          </div>

          <div>
            <div className="mb-1 text-xs font-semibold uppercase text-slate-400">Final context</div>
            <pre className="thin-scroll max-h-48 overflow-y-auto whitespace-pre-wrap rounded-xl bg-slate-900 p-3 text-[11px] leading-relaxed text-slate-100">
              {trace.data.final_context}
            </pre>
          </div>
        </div>
      )}
    </div>
  );
}

export default function AdminPage() {
  const [search, setSearch] = useState("");
  const [tab, setTab] = useState<"documents" | "debug">("documents");
  const stats = useQuery({
    queryKey: ["adminStats"],
    queryFn: api.adminStats,
  });
  const docs = useQuery({
    queryKey: ["documents", search],
    queryFn: () => api.documents(search || undefined),
  });

  const cards = [
    {
      label: "Total Documents",
      value: stats.data?.total_documents,
      icon: FileText,
      color: "bg-brand-50 text-brand-600",
    },
    {
      label: "Indexed",
      value: stats.data?.indexed_documents,
      icon: CheckCircle2,
      color: "bg-emerald-50 text-emerald-600",
    },
    {
      label: "Processing",
      value: stats.data?.processing_documents,
      icon: Loader2,
      color: "bg-amber-50 text-amber-600",
    },
    {
      label: "Failed",
      value: stats.data?.failed_documents,
      icon: XCircle,
      color: "bg-red-50 text-red-600",
    },
    {
      label: "Total Chunks",
      value: stats.data?.total_chunks,
      icon: Layers,
      color: "bg-indigo-50 text-indigo-600",
    },
  ];

  return (
    <div className="thin-scroll h-full overflow-y-auto">
      <div className="mx-auto max-w-6xl px-4 py-6">
        <div className="mb-6">
          <h1 className="text-xl font-bold text-slate-900">Admin Dashboard</h1>
          <p className="text-sm text-slate-500">
            Manage the document corpus powering the RAG assistant.
          </p>
        </div>

        {/* Stats cards */}
        <div className="mb-6 grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-5">
          {cards.map((c) => (
            <div key={c.label} className="rounded-2xl border bg-white p-4">
              <div
                className={`mb-2 inline-flex h-9 w-9 items-center justify-center rounded-xl ${c.color}`}
              >
                <c.icon className="h-4.5 w-4.5" />
              </div>
              <div className="text-2xl font-bold text-slate-900">
                {c.value ?? (stats.isLoading ? "…" : "0")}
              </div>
              <div className="text-xs font-medium text-slate-500">{c.label}</div>
            </div>
          ))}
        </div>

        <div className="mb-6 grid gap-2 rounded-2xl border bg-white p-4 text-sm sm:grid-cols-2">
          <div className="flex items-center gap-2">
            <Database className="h-4 w-4 text-slate-400" />
            LLM provider: <b className="text-slate-700">{stats.data?.llm_provider ?? "…"}</b>
          </div>
          <div className="flex items-center gap-2">
            <FileStack className="h-4 w-4 text-slate-400" />
            Embeddings: <b className="text-slate-700">{stats.data?.embedding_provider ?? "…"}</b>
          </div>
        </div>

        <KnowledgeStatsPanel />

        {/* Debug tab switch */}
        <div className="mt-6 mb-4 flex gap-2">
          <button
            onClick={() => setTab("documents")}
            className={`rounded-xl px-4 py-2 text-sm font-semibold transition ${
              tab === "documents"
                ? "bg-brand-600 text-white"
                : "bg-slate-100 text-slate-600 hover:bg-slate-200"
            }`}
          >
            Documents & ingestion
          </button>
          <button
            onClick={() => setTab("debug")}
            className={`rounded-xl px-4 py-2 text-sm font-semibold transition ${
              tab === "debug"
                ? "bg-brand-600 text-white"
                : "bg-slate-100 text-slate-600 hover:bg-slate-200"
            }`}
          >
            RAG debugging
          </button>
        </div>

        {tab === "debug" ? (
          <RagDebugPanel />
        ) : (
        <>
        <div className="grid gap-6 lg:grid-cols-2">
          <UploadForm />
          <div className="rounded-2xl border bg-white p-5">
            <h2 className="mb-1 font-bold text-slate-900">Ingestion pipeline</h2>
            <p className="mb-4 text-xs text-slate-500">
              Every upload moves through these tracked stages. Failures are recorded and visible
              in the table below.
            </p>
            <div className="flex flex-wrap items-center gap-1.5">
              {STATUS_STEPS.map((s, i) => (
                <div key={s} className="flex items-center gap-1.5">
                  <span
                    className={`rounded-full px-2.5 py-1 text-xs font-semibold ${
                      s === "indexed"
                        ? "bg-emerald-50 text-emerald-700"
                        : "bg-brand-50 text-brand-700"
                    }`}
                  >
                    {s}
                  </span>
                  {i < STATUS_STEPS.length - 1 && (
                    <span className="text-slate-300">→</span>
                  )}
                </div>
              ))}
              <span className="rounded-full bg-red-50 px-2.5 py-1 text-xs font-semibold text-red-600">
                failed
              </span>
            </div>
            <p className="mt-3 rounded-xl bg-slate-50 p-3 text-xs text-slate-500">
              Re-run ingestion any time with the <RefreshCw className="inline h-3 w-3" /> button
              (documents keep their file; chunks and embeddings are regenerated).
            </p>
          </div>
        </div>

        {/* Documents table */}
        <div className="mt-6 rounded-2xl border bg-white">
          <div className="flex flex-wrap items-center justify-between gap-3 border-b p-4">
            <h2 className="font-bold text-slate-900">Documents</h2>
            <div className="relative">
              <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
              <input
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder="Search documents…"
                className="rounded-xl border py-2 pl-9 pr-3 text-sm outline-none focus:border-brand-500"
              />
            </div>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full min-w-[720px] text-left">
              <thead>
                <tr className="border-b bg-slate-50 text-xs uppercase tracking-wide text-slate-500">
                  <th className="px-3 py-2.5 font-semibold">Title</th>
                  <th className="px-3 py-2.5 font-semibold">Standard</th>
                  <th className="px-3 py-2.5 font-semibold">Status</th>
                  <th className="px-3 py-2.5 font-semibold">Chunks</th>
                  <th className="px-3 py-2.5 font-semibold">Pages</th>
                  <th className="px-3 py-2.5 font-semibold">Actions</th>
                </tr>
              </thead>
              <tbody>
                {(docs.data ?? []).map((d) => (
                  <DocumentRow key={d.id} d={d} />
                ))}
                {docs.data && docs.data.length === 0 && (
                  <tr>
                    <td colSpan={6} className="px-3 py-8 text-center text-sm text-slate-400">
                      No documents yet — upload your first PDF above.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
        </>
        )}
      </div>
    </div>
  );
}
