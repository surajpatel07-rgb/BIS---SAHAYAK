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
  const [meta, setMeta] = useState({
    title: "",
    standard_number: "",
    year: "",
    document_type: "standard",
    category: "general",
    description: "",
    source_url: "",
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
        <input
          value={meta.category}
          onChange={(e) => setMeta({ ...meta, category: e.target.value })}
          placeholder="Category, e.g. cement, electronics"
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

export default function AdminPage() {
  const [search, setSearch] = useState("");
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
      </div>
    </div>
  );
}
