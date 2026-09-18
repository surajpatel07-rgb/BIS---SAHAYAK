import { useCallback, useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  AlertTriangle,
  Camera,
  CheckCircle2,
  FileText,
  ImageOff,
  Loader2,
  MessageSquarePlus,
  RefreshCw,
  ScanSearch,
  Search,
  Sparkles,
  Upload,
  X,
} from "lucide-react";
import { api, ApiError, openDocumentPdf } from "../services/api";
import type { ProductIdentificationResponse, StandardRecommendation } from "../services/api";

const MAX_MB = 8;
const ACCEPT = ".jpg,.jpeg,.png,.webp";

type Stage = 0 | 1 | 2 | 3;
const STAGES: { label: string; hint: string }[] = [
  { label: "Analyzing image", hint: "Preparing the photo for the vision model" },
  { label: "Identifying product", hint: "Recognising the product, brand and markings" },
  { label: "Matching BIS standards", hint: "Searching the indexed BIS knowledge base" },
  { label: "Validating evidence", hint: "Scoring relevance and preparing citations" },
];

function confidenceBand(confidence: number): "High" | "Medium" | "Low" {
  if (confidence >= 0.66) return "High";
  if (confidence >= 0.4) return "Medium";
  return "Low";
}

function ConfidenceBadge({ value }: { value: number }) {
  const band = confidenceBand(value);
  const styles = {
    High: "bg-emerald-50 text-emerald-700",
    Medium: "bg-amber-50 text-amber-700",
    Low: "bg-red-50 text-red-700",
  } as const;
  return (
    <span className={`rounded-full px-2 py-0.5 text-[11px] font-semibold ${styles[band]}`}>
      {band} confidence ({Math.round(value * 100)}%)
    </span>
  );
}

function StandardCard({
  rec,
  onAsk,
}: {
  rec: StandardRecommendation;
  onAsk: (r: StandardRecommendation) => void;
}) {
  const navigate = useNavigate();
  // New-tab PDF opening needs a short-lived scoped token (no auth header on
  // tab navigation). Failure shows a visible "Source unavailable" message.
  const openSource = () => openDocumentPdf(rec.document_id, rec.page);
  return (
    <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
      <div className="flex flex-wrap items-center gap-2">
        <span className="rounded-lg bg-brand-50 px-2 py-1 font-mono text-sm font-bold text-brand-700">
          {rec.is_number || "—"}
        </span>
        <span
          className={`rounded-full px-2 py-0.5 text-[11px] font-semibold ${
            rec.match_level === "strong"
              ? "bg-emerald-50 text-emerald-700"
              : rec.match_level === "moderate"
              ? "bg-amber-50 text-amber-700"
              : "bg-red-50 text-red-700"
          }`}
        >
          {rec.match_level} match
        </span>
        <ConfidenceBadge value={rec.confidence} />
      </div>

      <h4 className="mt-2 font-semibold text-slate-800">{rec.title}</h4>

      <dl className="mt-3 space-y-1.5 text-sm">
        <div>
          <dt className="inline font-medium text-slate-500">Relevance: </dt>
          <dd className="inline text-slate-700">{rec.relevance}</dd>
        </div>
        <div>
          <dt className="inline font-medium text-slate-500">Evidence: </dt>
          <dd className="inline text-slate-700">“{rec.evidence}”</dd>
        </div>
        <div>
          <dt className="inline font-medium text-slate-500">Source: </dt>
          <dd className="inline text-slate-700">{rec.source}</dd>
        </div>
      </dl>

      <p className="mt-2 text-[11px] text-slate-500">
        Potentially applicable standard — recommended for further verification on the
        official BIS source.
      </p>

      <div className="mt-3 flex flex-wrap gap-2">
        <button
          onClick={() => {
            openSource();
          }}
          className="inline-flex items-center gap-1.5 rounded-lg border border-slate-200 px-3 py-1.5 text-xs font-medium text-slate-600 transition hover:bg-slate-50"
        >
          <FileText size={13} /> View Source
        </button>
        <button
          onClick={() => onAsk(rec)}
          className="inline-flex items-center gap-1.5 rounded-lg bg-brand-600 px-3 py-1.5 text-xs font-semibold text-white transition hover:bg-brand-700"
        >
          <MessageSquarePlus size={13} /> Ask BIS Buddy
        </button>
        {rec.source_url && (
          <a
            href={rec.source_url}
            target="_blank"
            rel="noreferrer"
            className="inline-flex items-center gap-1.5 rounded-lg border border-slate-200 px-3 py-1.5 text-xs font-medium text-slate-600 transition hover:bg-slate-50"
          >
            <Search size={13} /> Official source
          </a>
        )}
      </div>
    </div>
  );
}

export default function ProductIdentifierPage() {
  const navigate = useNavigate();
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<string | null>(null);
  const [description, setDescription] = useState("");
  const [manualName, setManualName] = useState("");
  const [showManual, setShowManual] = useState(false);
  const [busy, setBusy] = useState(false);
  const [stage, setStage] = useState<Stage>(0);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<ProductIdentificationResponse | null>(null);
  const [pickedMatch, setPickedMatch] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const cameraInputRef = useRef<HTMLInputElement>(null);
  const stageTimer = useRef<ReturnType<typeof setInterval> | null>(null);
  const previewUrlRef = useRef<string | null>(null);

  const stopStages = useCallback(() => {
    if (stageTimer.current) {
      clearInterval(stageTimer.current);
      stageTimer.current = null;
    }
  }, []);

  useEffect(() => stopStages, [stopStages]);

  const pickFile = (f: File | null | undefined) => {
    if (!f) return;
    if (f.size > MAX_MB * 1024 * 1024) {
      setError(`Image too large (max ${MAX_MB} MB).`);
      return;
    }
    setError(null);
    setResult(null);
    setPickedMatch(null);
    setFile(f);
    if (previewUrlRef.current) URL.revokeObjectURL(previewUrlRef.current);
    const url = URL.createObjectURL(f);
    previewUrlRef.current = url;
    setPreview(url);
  };

  const identify = async () => {
    if (!file || busy) return;
    setError(null);
    setResult(null);
    setPickedMatch(null);
    setBusy(true);
    setStage(0);
    stageTimer.current = setInterval(
      () => setStage((s) => (s < 3 ? ((s + 1) as Stage) : s)),
      1600
    );
    try {
      const data = await api.identifyProduct(file, description.trim());
      setResult(data);
    } catch (e) {
      const msg =
        e instanceof ApiError
          ? e.message
          : "Network error — please check your connection and try again.";
      setError(msg);
    } finally {
      stopStages();
      setBusy(false);
      setStage(0);
    }
  };

  const matchManually = async (name: string) => {
    const trimmed = name.trim();
    if (trimmed.length < 2 || busy) return;
    setError(null);
    setResult(null);
    setBusy(true);
    setStage(2);
    try {
      const data = await api.matchProduct(trimmed);
      setResult(data);
      setPickedMatch(trimmed);
    } catch (e) {
      const msg =
        e instanceof ApiError
          ? e.message
          : "Network error — please check your connection and try again.";
      setError(msg);
    } finally {
      setBusy(false);
      setStage(0);
    }
  };

  const askBisBuddy = (rec: StandardRecommendation) => {
    const ctx = [
      `I identified a product (AI Product Identifier): ${result?.product.name || pickedMatch || "unknown product"}.`,
      `Recommended standard: ${rec.is_number || rec.title}.`,
      `Retrieved evidence: "${rec.evidence.slice(0, 220)}"`,
      `Source: ${rec.source}.`,
      "Please explain this standard and what it means for this product, citing the retrieved documents.",
    ].join("\n");
    navigate("/chat", { state: { prefill: ctx } });
  };

  const reset = () => {
    setFile(null);
    setResult(null);
    setPickedMatch(null);
    setError(null);
    setShowManual(false);
    setDescription("");
    if (previewUrlRef.current) {
      URL.revokeObjectURL(previewUrlRef.current);
      previewUrlRef.current = null;
    }
    setPreview(null);
  };

  const product = result?.product;

  return (
    <div className="mx-auto max-w-3xl space-y-6">
      {/* Header card */}
      <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
        <div className="flex items-start gap-4">
          <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-xl bg-brand-50 text-brand-600">
            <ScanSearch size={24} />
          </div>
          <div>
            <h1 className="text-xl font-bold text-slate-800">🔍 Identify Product from Image</h1>
            <p className="mt-1 text-sm text-slate-500">
              Upload a product photo to automatically identify the product and discover
              potentially applicable BIS Standards — with evidence from the indexed
              knowledge base.
            </p>
          </div>
        </div>
      </div>

      {/* Upload card */}
      <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
        {!preview ? (
          <div className="space-y-3">
            <button
              onClick={() => fileInputRef.current?.click()}
              className="flex w-full items-center justify-center gap-2 rounded-xl border-2 border-dashed border-slate-300 bg-slate-50 px-4 py-8 text-sm font-semibold text-slate-600 transition hover:border-brand-400 hover:bg-brand-50 hover:text-brand-700"
            >
              <Upload size={18} /> Upload Image
              <span className="text-xs font-normal text-slate-400">(JPG, PNG, WEBP · max {MAX_MB} MB)</span>
            </button>
            <button
              onClick={() => cameraInputRef.current?.click()}
              className="flex w-full items-center justify-center gap-2 rounded-xl border border-slate-200 px-4 py-3 text-sm font-medium text-slate-600 transition hover:bg-slate-50"
            >
              <Camera size={16} /> Take / Choose Photo
            </button>
          </div>
        ) : (
          <div className="space-y-4">
            <div className="relative overflow-hidden rounded-xl border border-slate-200">
              <img
                src={preview ?? undefined}
                alt="Product preview"
                className="mx-auto max-h-72 w-auto object-contain"
              />
              <button
                onClick={reset}
                className="absolute right-2 top-2 rounded-full bg-white/90 p-1.5 text-slate-500 shadow hover:text-slate-800"
                aria-label="Remove image"
              >
                <X size={16} />
              </button>
            </div>
            <input
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Optional: describe the product to help identification (e.g. 'steel water bottle, about 1 litre')"
              className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm outline-none focus:border-brand-400 focus:ring-2 focus:ring-brand-100"
            />
            <button
              onClick={identify}
              disabled={busy}
              className="inline-flex w-full items-center justify-center gap-2 rounded-xl bg-brand-600 px-4 py-3 text-sm font-semibold text-white transition hover:bg-brand-700 disabled:opacity-60"
            >
              {busy ? (
                <>
                  <Loader2 size={16} className="animate-spin" /> Analyzing…
                </>
              ) : (
                <>
                  <Sparkles size={16} /> Identify Product
                </>
              )}
            </button>
          </div>
        )}

        <input
          ref={fileInputRef}
          type="file"
          accept={ACCEPT}
          className="hidden"
          onChange={(e) => pickFile(e.target.files?.[0])}
        />
        <input
          ref={cameraInputRef}
          type="file"
          accept="image/*"
          capture="environment"
          className="hidden"
          onChange={(e) => pickFile(e.target.files?.[0])}
        />

        {/* Processing stages */}
        {busy && (
          <ol className="mt-5 space-y-2" aria-live="polite">
            {STAGES.map((s, i) => (
              <li key={s.label} className="flex items-center gap-2 text-sm">
                {i < stage ? (
                  <CheckCircle2 size={15} className="text-emerald-500" />
                ) : i === stage ? (
                  <Loader2 size={15} className="animate-spin text-brand-600" />
                ) : (
                  <span className="inline-block h-[15px] w-[15px] rounded-full border border-slate-300" />
                )}
                <span className={i <= stage ? "font-medium text-slate-700" : "text-slate-400"}>
                  {s.label}
                </span>
                {i === stage && <span className="text-xs text-slate-400">— {s.hint}</span>}
              </li>
            ))}
          </ol>
        )}

        {error && (
          <div className="mt-4 flex items-start gap-2 rounded-xl bg-red-50 p-3 text-sm text-red-700">
            <AlertTriangle size={16} className="mt-0.5 shrink-0" />
            <div>
              <p>{error}</p>
              <button
                onClick={reset}
                className="mt-2 inline-flex items-center gap-1 rounded-lg bg-red-100 px-2.5 py-1 text-xs font-semibold text-red-700 hover:bg-red-200"
              >
                <RefreshCw size={12} /> Try Again
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Results */}
      {result && (
        <>
          {/* Product identification card */}
          <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
            <h2 className="flex items-center gap-2 text-sm font-bold uppercase tracking-wide text-slate-400">
              <ScanSearch size={15} /> Product Identified
            </h2>

            {product?.name ? (
              <>
                <div className="mt-3 flex flex-wrap items-center gap-2">
                  <span className="text-lg font-bold text-slate-800">
                    {pickedMatch ?? product.name}
                  </span>
                  {product.category && (
                    <span className="rounded-full bg-slate-100 px-2.5 py-0.5 text-xs text-slate-600">
                      {product.category}
                    </span>
                  )}
                  <ConfidenceBadge value={product.confidence} />
                </div>

                {(product.product_type || product.brand || product.model) && (
                  <dl className="mt-3 grid grid-cols-1 gap-x-6 gap-y-1 text-sm sm:grid-cols-2">
                    {product.product_type && (
                      <div>
                        <dt className="inline font-medium text-slate-500">Type: </dt>
                        <dd className="inline text-slate-700">{product.product_type}</dd>
                      </div>
                    )}
                    {product.brand && (
                      <div>
                        <dt className="inline font-medium text-slate-500">Brand: </dt>
                        <dd className="inline text-slate-700">{product.brand}</dd>
                      </div>
                    )}
                    {product.model && (
                      <div>
                        <dt className="inline font-medium text-slate-500">Model: </dt>
                        <dd className="inline text-slate-700">{product.model}</dd>
                      </div>
                    )}
                    {product.packaging_info && (
                      <div>
                        <dt className="inline font-medium text-slate-500">Packaging: </dt>
                        <dd className="inline text-slate-700">{product.packaging_info}</dd>
                      </div>
                    )}
                  </dl>
                )}

                {product.specifications.length > 0 && (
                  <div className="mt-3">
                    <p className="text-xs font-semibold uppercase tracking-wide text-slate-400">
                      Visible specifications
                    </p>
                    <ul className="mt-1 list-inside list-disc text-sm text-slate-700">
                      {product.specifications.map((s) => (
                        <li key={s}>{s}</li>
                      ))}
                    </ul>
                  </div>
                )}

                {product.markings.length > 0 && (
                  <div className="mt-3">
                    <p className="text-xs font-semibold uppercase tracking-wide text-slate-400">
                      Visible marks / labels
                    </p>
                    <div className="mt-1 flex flex-wrap gap-1.5">
                      {product.markings.map((m) => (
                        <span
                          key={m}
                          className="rounded-full bg-emerald-50 px-2.5 py-0.5 text-xs text-emerald-700"
                        >
                          {m}
                        </span>
                      ))}
                    </div>
                  </div>
                )}

                {product.possible_matches.length > 0 && !pickedMatch && (
                  <div className="mt-4 rounded-xl bg-slate-50 p-4">
                    <p className="text-sm font-semibold text-slate-700">Possible matches</p>
                    <p className="text-xs text-slate-500">
                      Not what you meant? Select the correct product to re-run matching.
                    </p>
                    <ul className="mt-2 space-y-1.5">
                      {product.possible_matches.map((m) => (
                        <li key={m.name}>
                          <button
                            onClick={() => matchManually(m.name)}
                            className="flex w-full items-center justify-between rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm transition hover:border-brand-300 hover:bg-brand-50"
                          >
                            <span>{m.name}</span>
                            <span className="text-xs font-semibold text-slate-500">
                              {Math.round(m.confidence * 100)}%
                            </span>
                          </button>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
              </>
            ) : (
              <div className="mt-3">
                <div className="flex items-start gap-2 rounded-xl bg-amber-50 p-4 text-sm text-amber-800">
                  <ImageOff size={18} className="mt-0.5 shrink-0" />
                  <div>
                    <p className="font-semibold">
                      We couldn't confidently identify this product.
                    </p>
                    <ul className="mt-1 list-inside list-disc text-xs">
                      <li>Upload a clearer image</li>
                      <li>Capture the full product</li>
                      <li>Include the product label/package</li>
                      <li>Or enter the product name manually below</li>
                    </ul>
                  </div>
                </div>
                <button
                  onClick={reset}
                  className="mt-3 inline-flex items-center gap-1.5 rounded-lg bg-brand-600 px-3 py-2 text-xs font-semibold text-white hover:bg-brand-700"
                >
                  <RefreshCw size={13} /> Try Again
                </button>
              </div>
            )}
          </div>

          {/* Warnings */}
          {result.warnings.length > 0 && (
            <div className="rounded-2xl border border-amber-200 bg-amber-50 p-4">
              <p className="flex items-center gap-1.5 text-sm font-semibold text-amber-800">
                <AlertTriangle size={15} /> Please note
              </p>
              <ul className="mt-1.5 list-inside list-disc space-y-1 text-sm text-amber-800">
                {result.warnings.map((w) => (
                  <li key={w}>{w}</li>
                ))}
              </ul>
            </div>
          )}

          {/* Standards results */}
          <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
            <h2 className="flex items-center gap-2 text-sm font-bold uppercase tracking-wide text-slate-400">
              <FileText size={15} /> Applicable BIS Standards
            </h2>

            {result.standards.length > 0 ? (
              <div className="mt-4 space-y-4">
                {result.standards.map((rec) => (
                  <StandardCard
                    key={`${rec.document_id}-${rec.page}-${rec.is_number}`}
                    rec={rec}
                    onAsk={askBisBuddy}
                  />
                ))}
                <p className="text-xs text-slate-400">
                  Standard recommendations are derived from the indexed BIS knowledge
                  base ({result.query_used}). Applicability should be verified on the
                  official BIS portal.
                </p>
              </div>
            ) : (
              <div className="mt-4 rounded-xl bg-slate-50 p-4">
                <p className="text-sm text-slate-600">
                  No sufficiently relevant BIS Standard was found in the current
                  knowledge base. This does not necessarily mean that no applicable
                  standard exists.
                </p>
                <div className="mt-3 flex flex-wrap gap-2">
                  <button
                    onClick={() => navigate("/documents")}
                    className="inline-flex items-center gap-1.5 rounded-lg bg-brand-600 px-3 py-2 text-xs font-semibold text-white hover:bg-brand-700"
                  >
                    <Search size={13} /> Search BIS Knowledge Base
                  </button>
                  <button
                    onClick={() => {
                      setShowManual(true);
                      setManualName(product?.name || pickedMatch || "");
                    }}
                    className="inline-flex items-center gap-1.5 rounded-lg border border-slate-200 px-3 py-2 text-xs font-medium text-slate-600 hover:bg-slate-50"
                  >
                    <RefreshCw size={13} /> Retry with a different product name
                  </button>
                </div>
              </div>
            )}
          </div>
        </>
      )}

      {/* Manual fallback — always available, result or not */}
      <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
        {showManual || !result?.product?.name ? (
          <div>
            <p className="text-sm font-semibold text-slate-700">
              Can't identify the product? Enter product name manually
            </p>
            <div className="mt-2 flex gap-2">
              <input
                value={manualName}
                onChange={(e) => setManualName(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && matchManually(manualName)}
                placeholder="e.g. pressure cooker, electric kettle, LED bulb"
                className="flex-1 rounded-lg border border-slate-200 px-3 py-2 text-sm outline-none focus:border-brand-400 focus:ring-2 focus:ring-brand-100"
              />
              <button
                onClick={() => matchManually(manualName)}
                disabled={busy || manualName.trim().length < 2}
                className="rounded-lg bg-brand-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-brand-700 disabled:opacity-60"
              >
                Match
              </button>
            </div>
          </div>
        ) : (
          <button
            onClick={() => setShowManual(true)}
            className="text-sm font-medium text-brand-600 hover:text-brand-700"
          >
            Can't identify the product? Enter product name manually →
          </button>
        )}
      </div>
    </div>
  );
}
