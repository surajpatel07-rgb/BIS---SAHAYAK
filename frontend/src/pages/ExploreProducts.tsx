import { useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import {
  ArrowLeft,
  BookOpen,
  FileText,
  Info,
  Loader2,
  Search,
  ShieldAlert,
  ShieldCheck,
} from "lucide-react";
import { api } from "../services/api";

export function CategoryCards() {
  const navigate = useNavigate();
  const categories = useQuery({ queryKey: ["categories"], queryFn: api.categories });

  return (
    <div className="thin-scroll h-full overflow-y-auto">
      <div className="mx-auto max-w-5xl px-4 py-6">
        <div className="mb-6">
          <h1 className="text-xl font-bold text-slate-900">Explore Products</h1>
          <p className="text-sm text-slate-500">
            Browse the knowledge base by category — standards, certification status and
            consumer checklists.{" "}
            <span className="text-slate-400">
              Reference data is DEMO-labelled; verify on official BIS sources.
            </span>
          </p>
        </div>

        {categories.isLoading && (
          <div className="flex items-center gap-2 rounded-xl border bg-white p-4 text-sm text-slate-500">
            <Loader2 className="h-4 w-4 animate-spin" /> Loading categories…
          </div>
        )}

        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {(categories.data ?? []).map((c) => (
            <button
              key={c.key}
              onClick={() => navigate(`/explore/${c.key}`)}
              className="rounded-2xl border bg-white p-5 text-left transition hover:border-brand-500 hover:shadow-sm"
            >
              <div className="text-3xl">{c.emoji}</div>
              <div className="mt-2 font-bold text-slate-800">{c.label}</div>
              <p className="mt-1 line-clamp-2 text-xs text-slate-500">{c.description}</p>
              <div className="mt-3 text-xs font-semibold text-brand-600">
                {c.document_count} indexed document{c.document_count === 1 ? "" : "s"} →
              </div>
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}

export function CategoryProducts() {
  const { categoryKey } = useParams();
  const navigate = useNavigate();
  const [q, setQ] = useState("");
  const categories = useQuery({ queryKey: ["categories"], queryFn: api.categories });
  const products = useQuery({
    queryKey: ["products", categoryKey, q],
    queryFn: () => api.products(categoryKey, q || undefined),
  });
  const cat = categories.data?.find((c) => c.key === categoryKey);

  return (
    <div className="thin-scroll h-full overflow-y-auto">
      <div className="mx-auto max-w-5xl px-4 py-6">
        <button
          onClick={() => navigate(-1)}
          className="mb-3 inline-flex items-center gap-1 text-sm text-slate-500 hover:text-brand-700"
        >
          <ArrowLeft className="h-4 w-4" /> All categories
        </button>

        <div className="mb-5 flex flex-wrap items-center gap-3">
          <div className="text-4xl">{cat?.emoji ?? "📁"}</div>
          <div>
            <h1 className="text-xl font-bold text-slate-900">
              {cat?.label ?? categoryKey}
            </h1>
            <p className="text-sm text-slate-500">{cat?.description}</p>
          </div>
        </div>

        <div className="mb-4 flex flex-wrap gap-2">
          {categories.data
            ?.filter((c) => c.key !== categoryKey)
            .map((c) => (
              <button
                key={c.key}
                onClick={() => navigate(`/explore/${c.key}`)}
                className="rounded-full bg-slate-100 px-3 py-1 text-xs text-slate-600 hover:bg-slate-200"
              >
                {c.emoji} {c.label}
              </button>
            ))}
        </div>

        <div className="mb-4 flex items-center gap-2 rounded-xl border bg-white px-3 py-2">
          <Search className="h-4 w-4 text-slate-400" />
          <input
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder="Search products in this category…"
            className="w-full text-sm outline-none"
          />
        </div>

        {products.isLoading && (
          <div className="flex items-center gap-2 rounded-xl border bg-white p-4 text-sm text-slate-500">
            <Loader2 className="h-4 w-4 animate-spin" /> Loading products…
          </div>
        )}

        <div className="grid gap-3 sm:grid-cols-2">
          {(products.data ?? []).map((p) => (
            <Link
              key={p.id}
              to={`/explore/product/${p.id}`}
              className="block rounded-2xl border bg-white p-4 transition hover:border-brand-500 hover:shadow-sm"
            >
              <div className="flex items-center justify-between gap-2">
                <div className="font-semibold text-slate-800">{p.name}</div>
                {p.certification_status === "mandatory" ? (
                  <ShieldCheck className="h-4 w-4 shrink-0 text-emerald-500" />
                ) : (
                  <ShieldAlert className="h-4 w-4 shrink-0 text-slate-300" />
                )}
              </div>
              <div className="mt-1 text-xs text-slate-500">{p.subcategory}</div>
              {p.standard_number ? (
                <div className="mt-2">
                  <span className="rounded bg-brand-50 px-2 py-0.5 text-xs font-bold text-brand-700">
                    {p.standard_number}
                  </span>
                </div>
              ) : (
                <div className="mt-2 text-xs italic text-slate-400">
                  Information not available in the current knowledge base
                </div>
              )}
            </Link>
          ))}
        </div>

        {products.data && products.data.length === 0 && (
          <div className="rounded-xl border bg-white p-6 text-sm text-slate-500">
            No products in this category yet.
          </div>
        )}
      </div>
    </div>
  );
}

export function ProductDetailPage() {
  const { productId } = useParams();
  const navigate = useNavigate();
  const product = useQuery({
    queryKey: ["product", productId],
    queryFn: () => api.product(Number(productId)),
    enabled: !!productId,
  });

  if (product.isLoading) {
    return (
      <div className="flex h-full items-center justify-center text-slate-500">
        <Loader2 className="h-5 w-5 animate-spin" />
      </div>
    );
  }
  if (!product.data) {
    return (
      <div className="flex h-full items-center justify-center text-sm text-slate-500">
        Product not found.
      </div>
    );
  }
  const p = product.data;

  return (
    <div className="thin-scroll h-full overflow-y-auto">
      <div className="mx-auto max-w-3xl px-4 py-6">
        <button
          onClick={() => navigate(-1)}
          className="mb-3 inline-flex items-center gap-1 text-sm text-slate-500 hover:text-brand-700"
        >
          <ArrowLeft className="h-4 w-4" /> Back
        </button>

        <div className="rounded-2xl border bg-white p-6">
          <div className="flex flex-wrap items-center gap-2 text-xs text-slate-500">
            <span className="rounded-full bg-slate-100 px-2 py-0.5">
              {p.category_emoji} {p.category_label}
            </span>
            {p.subcategory && <span>· {p.subcategory}</span>}
          </div>
          <h1 className="mt-2 text-2xl font-bold text-slate-900">{p.name}</h1>

          {/* Standard */}
          <div className="mt-4 rounded-xl bg-slate-50 p-4">
            <div className="text-[11px] font-semibold uppercase tracking-wide text-slate-400">
              Relevant standard
            </div>
            {p.standard_number ? (
              <>
                <div className="mt-1 text-lg font-bold text-brand-700">
                  {p.standard_number}
                </div>
                <div className="text-sm text-slate-600">{p.standard_title}</div>
              </>
            ) : (
              <div className="mt-1 flex items-start gap-2 text-sm italic text-slate-500">
                <Info className="mt-0.5 h-4 w-4 shrink-0" />
                Information not available in the current knowledge base.
              </div>
            )}
          </div>

          {/* Certification status */}
          <div className="mt-3 rounded-xl border p-4">
            <div className="text-[11px] font-semibold uppercase tracking-wide text-slate-400">
              Certification information
            </div>
            <div
              className={`mt-1 text-sm font-semibold ${
                p.certification_status === "mandatory"
                  ? "text-emerald-700"
                  : p.certification_status === "voluntary"
                  ? "text-amber-700"
                  : "text-slate-500"
              }`}
            >
              {p.certification_status_display}
            </div>
            {p.scheme && (
              <div className="mt-1 text-xs text-slate-500">
                Scheme: {p.scheme === "HALLMARK" ? "BIS Hallmarking" : p.scheme}
              </div>
            )}
            {p.notes && <p className="mt-2 text-xs text-slate-500">{p.notes}</p>}
          </div>

          {/* Consumer checklist */}
          {(p.consumer_checklist ?? []).length > 0 && (
            <div className="mt-3 rounded-xl border p-4">
              <div className="text-[11px] font-semibold uppercase tracking-wide text-slate-400">
                What you should check
              </div>
              <ul className="mt-2 list-disc space-y-1 pl-5 text-sm text-slate-700">
                {p.consumer_checklist.map((item) => (
                  <li key={item}>{item}</li>
                ))}
              </ul>
            </div>
          )}

          {/* Related documents */}
          <div className="mt-3 rounded-xl border p-4">
            <div className="text-[11px] font-semibold uppercase tracking-wide text-slate-400">
              Related documents in the knowledge base
            </div>
            {(p.related_documents ?? []).length === 0 && (
              <div className="mt-2 text-sm italic text-slate-400">
                Information not available in the current knowledge base.
              </div>
            )}
            <div className="mt-2 grid gap-2">
              {(p.related_documents ?? []).map((d) => (
                <Link
                  key={d.id}
                  to={`/documents/${d.id}`}
                  className="flex items-center gap-3 rounded-lg border bg-white p-3 transition hover:border-brand-500"
                >
                  <FileText className="h-4 w-4 shrink-0 text-brand-500" />
                  <div className="min-w-0 flex-1">
                    <div className="truncate text-sm font-semibold text-slate-800">
                      {d.standard_number || d.name}
                    </div>
                    <div className="truncate text-xs text-slate-500">{d.title}</div>
                  </div>
                  <span
                    className={`shrink-0 rounded px-1.5 py-0.5 text-[10px] font-bold ${
                      d.source_type === "demo"
                        ? "bg-amber-50 text-amber-700"
                        : "bg-emerald-50 text-emerald-700"
                    }`}
                  >
                    {d.source_type === "demo" ? "DEMO DATA" : "OFFICIAL SOURCE"}
                  </span>
                </Link>
              ))}
            </div>
          </div>

          {/* Related questions */}
          {(p.related_questions ?? []).length > 0 && (
            <div className="mt-3 rounded-xl border p-4">
              <div className="text-[11px] font-semibold uppercase tracking-wide text-slate-400">
                Ask BIS Buddy
              </div>
              <div className="mt-2 flex flex-wrap gap-1.5">
                {p.related_questions.map((qq) => (
                  <Link
                    key={qq}
                    to="/chat"
                    className="rounded-full border bg-slate-50 px-3 py-1 text-xs text-slate-600 transition hover:border-brand-500 hover:bg-brand-50"
                  >
                    {qq}
                  </Link>
                ))}
              </div>
            </div>
          )}

          <p className="mt-4 flex items-start gap-2 text-[11px] text-slate-400">
            <BookOpen className="mt-0.5 h-3.5 w-3.5 shrink-0" />
            Reference data for the demo knowledge base. Always verify against the official
            BIS portal (bis.gov.in / manakonline) before making decisions.
          </p>
        </div>
      </div>
    </div>
  );
}
