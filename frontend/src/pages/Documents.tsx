import { useState } from "react";
import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { FileText, Loader2, Search, SearchX, Upload } from "lucide-react";
import { api } from "../services/api";
import { useAuth } from "../context/AuthContext";

function StatusBadge({ status }: { status: string }) {
  const styles: Record<string, string> = {
    indexed: "bg-emerald-50 text-emerald-700",
    failed: "bg-red-50 text-red-700",
    processing: "bg-amber-50 text-amber-700",
    uploaded: "bg-slate-100 text-slate-600",
    extracting: "bg-sky-50 text-sky-700",
    chunking: "bg-sky-50 text-sky-700",
    embedding: "bg-indigo-50 text-indigo-700",
  };
  return (
    <span
      className={`rounded-full px-2 py-0.5 text-[11px] font-semibold ${
        styles[status] ?? "bg-slate-100 text-slate-600"
      }`}
    >
      {status}
    </span>
  );
}

export { StatusBadge };

/** The six knowledge-category filter chips (live from the registry-backed API). */
export function CategoryChips({
  selected,
  onPick,
}: {
  selected: string;
  onPick: (key: string) => void;
}) {
  const categories = useQuery({ queryKey: ["categories"], queryFn: api.categories });
  return (
    <>
      <button
        onClick={() => onPick("")}
        className={`rounded-full px-3 py-1 text-xs font-medium transition ${
          selected === ""
            ? "bg-brand-600 text-white"
            : "bg-slate-100 text-slate-600 hover:bg-slate-200"
        }`}
      >
        All
      </button>
      {(categories.data ?? []).map((c) => (
        <button
          key={c.key}
          onClick={() => onPick(c.key)}
          className={`rounded-full px-3 py-1 text-xs font-medium transition ${
            selected === c.key
              ? "bg-brand-600 text-white"
              : "bg-slate-100 text-slate-600 hover:bg-slate-200"
          }`}
        >
          {c.emoji} {c.label}
        </button>
      ))}
    </>
  );
}

export default function DocumentsPage() {
  const { user } = useAuth();
  const [q, setQ] = useState("");
  const [category, setCategory] = useState("");
  const [docType, setDocType] = useState("");
  const [semantic, setSemantic] = useState(false);

  const docs = useQuery({
    queryKey: ["documents", q, category, docType],
    queryFn: () => api.documentSearch(q || undefined, category || undefined, docType || undefined),
  });

  const semanticResults = useQuery({
    queryKey: ["semantic", q],
    queryFn: () => api.semanticSearch(q),
    enabled: semantic && q.trim().length > 2,
  });

  return (
    <div className="thin-scroll h-full overflow-y-auto">
      <div className="mx-auto max-w-5xl px-4 py-6">
        <div className="mb-6 flex flex-wrap items-center justify-between gap-3">
          <div>
            <h1 className="text-xl font-bold text-slate-900">Documents & Standards</h1>
            <p className="text-sm text-slate-500">
              Browse indexed BIS-related documents or search their content semantically.
            </p>
          </div>
          {user?.role === "admin" && (
            <Link
              to="/admin"
              className="inline-flex items-center gap-2 rounded-xl bg-brand-600 px-4 py-2 text-sm font-semibold text-white hover:bg-brand-700"
            >
              <Upload className="h-4 w-4" /> Manage / Upload
            </Link>
          )}
        </div>

        {/* Search bar */}
        <div className="rounded-2xl border bg-white p-4">
          <div className="flex gap-2">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
              <input
                value={q}
                onChange={(e) => setQ(e.target.value)}
                placeholder='Search by standard number, title, keyword… e.g. "IS 1234" or "setting time"'
                className="w-full rounded-xl border py-2.5 pl-9 pr-3 text-sm outline-none focus:border-brand-500 focus:ring-2 focus:ring-brand-100"
              />
            </div>
            <button
              onClick={() => setSemantic((s) => !s)}
              className={`rounded-xl px-4 py-2 text-sm font-semibold transition ${
                semantic
                  ? "bg-brand-600 text-white"
                  : "bg-slate-100 text-slate-600 hover:bg-slate-200"
              }`}
              title="Toggle semantic (AI) search over document chunks"
            >
              {semantic ? "Semantic ON" : "Semantic OFF"}
            </button>
          </div>
          <div className="mt-3 flex flex-wrap gap-2">
            <CategoryChips selected={category} onPick={setCategory} />
          </div>
        </div>

        {/* Semantic results */}
        {semantic && q.trim().length > 2 && (
          <div className="mt-4">
            <h2 className="mb-2 text-sm font-bold text-slate-700">
              Semantic matches (chunk-level)
            </h2>
            {semanticResults.isLoading && (
              <div className="flex items-center gap-2 rounded-xl border bg-white p-4 text-sm text-slate-500">
                <Loader2 className="h-4 w-4 animate-spin" /> Searching indexed chunks…
              </div>
            )}
            {(semanticResults.data?.results ?? []).map((h, i) => (
              <Link
                key={i}
                to={`/documents/${h.document_id}`}
                className="mb-2 block rounded-xl border bg-white p-4 transition hover:border-brand-500"
              >
                <div className="flex flex-wrap items-center gap-2 text-xs text-slate-500">
                  <span className="rounded bg-brand-50 px-1.5 py-0.5 font-bold text-brand-700">
                    {h.standard_number || h.document_name}
                  </span>
                  <span>Page {h.page}</span>
                  {h.section && <span className="truncate">· {h.section}</span>}
                  <span className="ml-auto rounded bg-emerald-50 px-1.5 py-0.5 text-emerald-700">
                    {(h.score * 100).toFixed(0)}%
                  </span>
                </div>
                <p className="mt-1.5 line-clamp-2 text-sm text-slate-700">{h.snippet}</p>
              </Link>
            ))}
            {semanticResults.data && semanticResults.data.results.length === 0 && (
              <div className="rounded-xl border bg-white p-4 text-sm text-slate-500">
                No semantic matches. Try different keywords or upload the relevant document.
              </div>
            )}
          </div>
        )}

        {/* Document list */}
        <div className="mt-6">
          <h2 className="mb-2 text-sm font-bold text-slate-700">Documents</h2>
          {docs.isLoading && (
            <div className="flex items-center gap-2 rounded-xl border bg-white p-4 text-sm text-slate-500">
              <Loader2 className="h-4 w-4 animate-spin" /> Loading documents…
            </div>
          )}
          {docs.data && docs.data.length === 0 && (
            <div className="flex items-center gap-2 rounded-xl border bg-white p-6 text-sm text-slate-500">
              <SearchX className="h-4 w-4" /> No documents match your search.
            </div>
          )}
          <div className="grid gap-3">
            {(docs.data ?? []).map((d) => (
              <Link
                key={d.id}
                to={`/documents/${d.id}`}
                className="flex items-center gap-4 rounded-2xl border bg-white p-4 transition hover:border-brand-500 hover:shadow-sm"
              >
                <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-brand-50">
                  <FileText className="h-5 w-5 text-brand-600" />
                </div>
                <div className="min-w-0 flex-1">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="rounded bg-brand-50 px-2 py-0.5 text-xs font-bold text-brand-700">
                      {d.standard_number || "—"}
                    </span>
                    <StatusBadge status={d.status} />
                    <span className="rounded bg-slate-100 px-2 py-0.5 text-[11px] uppercase text-slate-500">
                      {d.document_type}
                    </span>
                  </div>
                  <div className="mt-1 truncate font-semibold text-slate-800">{d.title}</div>
                  <div className="text-xs text-slate-500">
                    {d.name} {d.year ? `· ${d.year}` : ""} · {d.page_count} pages ·{" "}
                    {d.chunk_count ?? 0} chunks · {d.category}
                  </div>
                </div>
              </Link>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
