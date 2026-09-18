import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import {
  ArrowLeft,
  Calendar,
  ExternalLink,
  FileText,
  Layers,
  Link2,
  Loader2,
} from "lucide-react";
import { api } from "../services/api";
import { StatusBadge } from "./Documents";

export default function DocumentDetailPage() {
  const { documentId } = useParams();
  const id = Number(documentId);
  const doc = useQuery({
    queryKey: ["document", id],
    queryFn: () => api.document(id),
  });
  const [page, setPage] = useState<number>(1);
  // The PDF <iframe> navigates like a tab: no Authorization header is sent,
  // so mint a short-lived document-scoped token for it.
  const [tokenUrl, setTokenUrl] = useState<string | null>(null);
  const [fileError, setFileError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setTokenUrl(null);
    setFileError(null);
    api.documentFileTokenUrl(id)
      .then((url) => {
        if (!cancelled) setTokenUrl(url);
      })
      .catch(() => {
        if (!cancelled) {
          setFileError("Source unavailable — the PDF viewer could not be loaded.");
        }
      });
    return () => {
      cancelled = true;
    };
  }, [id]);

  if (doc.isLoading) {
    return (
      <div className="flex h-full items-center justify-center text-slate-500">
        <Loader2 className="mr-2 h-5 w-5 animate-spin" /> Loading document…
      </div>
    );
  }
  if (doc.isError || !doc.data) {
    return (
      <div className="flex h-full flex-col items-center justify-center gap-3 text-slate-500">
        <p>Document not found.</p>
        <Link to="/documents" className="font-semibold text-brand-600 hover:underline">
          ← Back to documents
        </Link>
      </div>
    );
  }

  const d = doc.data;
  const fileUrl = tokenUrl ?? api.documentFileUrl(d.id);

  return (
    <div className="thin-scroll h-full overflow-y-auto">
      <div className="mx-auto max-w-6xl px-4 py-6">
        <Link
          to="/documents"
          className="mb-4 inline-flex items-center gap-1 text-sm font-medium text-brand-600 hover:text-brand-800"
        >
          <ArrowLeft className="h-4 w-4" /> All documents
        </Link>

        <div className="grid gap-6 lg:grid-cols-5">
          {/* Metadata */}
          <div className="lg:col-span-2">
            <div className="rounded-2xl border bg-white p-5">
              <div className="mb-3 flex items-start justify-between gap-2">
                <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-brand-50">
                  <FileText className="h-6 w-6 text-brand-600" />
                </div>
                <StatusBadge status={d.status} />
              </div>
              <h1 className="text-lg font-bold text-slate-900">{d.title || d.name}</h1>
              <p className="text-sm text-slate-500">{d.name}</p>

              <dl className="mt-4 space-y-2.5 text-sm">
                {[
                  ["Standard number", d.standard_number || "—"],
                  ["Year", d.year ? String(d.year) : "—"],
                  ["Type", d.document_type],
                  ["Category", d.category],
                  ["Pages", String(d.page_count)],
                  ["Chunks", String(d.chunk_count ?? 0)],
                  ["Size", `${(d.file_size / 1024).toFixed(0)} KB`],
                ].map(([k, v]) => (
                  <div key={k} className="flex justify-between gap-3">
                    <dt className="text-slate-500">{k}</dt>
                    <dd className="font-medium text-slate-800">{v}</dd>
                  </div>
                ))}
                {d.source_url && (
                  <div className="flex justify-between gap-3">
                    <dt className="text-slate-500">Source</dt>
                    <dd>
                      <a
                        href={d.source_url}
                        target="_blank"
                        rel="noreferrer"
                        className="inline-flex items-center gap-1 font-medium text-brand-600 hover:underline"
                      >
                        link <ExternalLink className="h-3 w-3" />
                      </a>
                    </dd>
                  </div>
                )}
              </dl>

              {d.description && (
                <p className="mt-4 rounded-xl bg-slate-50 p-3 text-sm text-slate-600">
                  {d.description}
                </p>
              )}
              {d.status === "failed" && d.error_message && (
                <p className="mt-4 rounded-xl bg-red-50 p-3 text-sm text-red-700">
                  <b>Ingestion failed:</b> {d.error_message}
                </p>
              )}

              <a
                href={fileUrl}
                target="_blank"
                rel="noreferrer"
                className="mt-4 inline-flex w-full items-center justify-center gap-2 rounded-xl bg-brand-600 px-4 py-2.5 text-sm font-semibold text-white hover:bg-brand-700"
              >
                <Link2 className="h-4 w-4" /> Open PDF
              </a>
            </div>
          </div>

          {/* PDF viewer + chunks */}
          <div className="lg:col-span-3">
            {d.status === "indexed" ? (
              <div className="overflow-hidden rounded-2xl border bg-white">
                <div className="flex items-center justify-between border-b px-4 py-2.5">
                  <div className="flex items-center gap-2 text-sm font-semibold text-slate-700">
                    <Layers className="h-4 w-4 text-brand-600" /> Document viewer
                  </div>
                  <div className="flex items-center gap-2 text-sm">
                    <button
                      onClick={() => setPage((p) => Math.max(1, p - 1))}
                      className="rounded-lg border px-2.5 py-1 hover:bg-slate-50"
                    >
                      ‹
                    </button>
                    <span className="text-slate-600">
                      page {page} / {Math.max(d.page_count, 1)}
                    </span>
                    <button
                      onClick={() => setPage((p) => Math.min(d.page_count, p + 1))}
                      className="rounded-lg border px-2.5 py-1 hover:bg-slate-50"
                    >
                      ›
                    </button>
                  </div>
                </div>
                {fileError ? (
                  <div className="flex h-[280px] flex-col items-center justify-center gap-2 bg-slate-50 text-sm text-slate-500">
                    <FileText className="h-8 w-8 text-slate-300" />
                    <p className="font-semibold text-slate-600">Source unavailable</p>
                    <p className="text-xs">{fileError}</p>
                  </div>
                ) : !tokenUrl ? (
                  <div className="flex h-[280px] items-center justify-center bg-slate-50 text-sm text-slate-400">
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" /> Loading PDF…
                  </div>
                ) : (
                  <iframe
                    key={`${page}-${tokenUrl}`}
                    src={`${fileUrl}#page=${page}`}
                    title="PDF preview"
                    className="h-[560px] w-full"
                  />
                )}
                <div className="border-t bg-slate-50 px-4 py-2 text-xs text-slate-500">
                  Citations in chat link directly to the page shown here
                  ({`/#page=n`} behavior depends on your browser's PDF plugin).
                </div>
              </div>
            ) : (
              <div className="rounded-2xl border bg-white p-6 text-sm text-slate-500">
                The document viewer is available once this document is indexed
                (current status: <b>{d.status}</b>).
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
