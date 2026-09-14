/** Typed API client for the BIS Buddy backend. */

export interface UserInfo {
  id: number;
  name: string;
  email: string;
  role: "user" | "admin";
}

export interface Citation {
  document_id: number;
  document_name: string;
  standard_number: string;
  title: string;
  page: number;
  section: string;
  chunk_id: number;
  relevance_score: number;
  source_url: string;
  document_type: string;
  category: string;
  year: number | null;
  snippet: string;
}

export interface ChatResponse {
  conversation_id: number;
  message_id: number;
  answer: string;
  sources: Citation[];
  mode: string;
  llm_provider: string;
  detected_category?: string;
  category_label?: string;
  category_confidence?: number;
  language?: string;
  related_questions?: string[];
}

export interface ConversationSummary {
  id: number;
  title: string;
  mode: string;
  created_at: string;
  updated_at: string;
}

export interface MessageOut {
  id: number;
  role: "user" | "assistant";
  content: string;
  sources_json: { sources?: Citation[] } | null;
  created_at: string;
}

export interface ConversationDetail extends ConversationSummary {
  messages: MessageOut[];
}

export interface DocumentOut {
  id: number;
  name: string;
  standard_number: string;
  title: string;
  year: number | null;
  document_type: string;
  category: string;
  description: string;
  file_path: string;
  file_size: number;
  page_count: number;
  source_url: string;
  status: string;
  error_message: string;
  created_at: string;
  updated_at: string;
  chunk_count?: number;
}

export interface AdminStats {
  total_documents: number;
  indexed_documents: number;
  processing_documents: number;
  failed_documents: number;
  total_chunks: number;
  total_conversations: number;
  total_messages: number;
  total_users: number;
  llm_provider: string;
  embedding_provider: string;
}

export interface SearchHit {
  document_id: number;
  document_name: string;
  standard_number: string;
  title: string;
  page: number;
  section: string;
  snippet: string;
  score: number;
  category?: string;
  year?: number | null;
}

// ---- Knowledge base -------------------------------------------------------
export interface KnowledgeCategory {
  key: string;
  label: string;
  emoji: string;
  description: string;
  document_count: number;
}

export interface ProductSummary {
  id: number;
  name: string;
  category: string;
  category_label: string;
  category_emoji: string;
  subcategory: string;
  standard_number: string;
  standard_title: string;
  certification_status: string;
  certification_status_display: string;
  scheme: string;
  consumer_checklist: string[];
  notes: string;
  info_available: boolean;
}

export interface ProductDetail extends ProductSummary {
  related_documents: {
    id: number;
    name: string;
    standard_number: string;
    title: string;
    year: number | null;
    source_type: string;
    source_name: string;
  }[];
  related_questions: string[];
}

export interface KnowledgeStats {
  categories: {
    key: string;
    label: string;
    emoji: string;
    documents: number;
    indexed: number;
    chunks: number;
    failed: number;
  }[];
  total_products: number;
  total_standards: number;
  last_updated: string | null;
}

export interface RagDebugTrace {
  query: string;
  language: string;
  detected_category: string;
  category_confidence: number;
  matched_keywords: string[];
  matched_product: string;
  detected_standard: string;
  category_filter_applied: boolean;
  candidates_before_rerank: {
    document_id: number;
    document_name: string;
    standard_number: string;
    page: number;
    section: string;
    category: string;
    source_type: string;
    vector_score: number;
  }[];
  selected_chunks: {
    document_id: number;
    document_name: string;
    standard_number: string;
    page: number;
    section: string;
    category: string;
    final_score: number;
    snippet: string;
  }[];
  final_context: string;
  embedding_model: string;
  top_k: number;
  rerank_top_n: number;
}

/**
 * API base URL.
 * - unset/empty  → same-origin (Vite dev proxy locally, or backend-served SPA)
 * - set in prod  → e.g. https://bis-sahayak-jbim.onrender.com (Vercel deploy)
 */
const BASE = (import.meta.env.VITE_API_BASE_URL ?? "").replace(/\/+$/, "");

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

async function request<T>(
  path: string,
  options: RequestInit & { auth?: boolean } = {}
): Promise<T> {
  const { auth = true, ...rest } = options;
  const headers: Record<string, string> = {
    ...(rest.headers as Record<string, string>),
  };
  if (rest.body && !(rest.body instanceof FormData)) {
    headers["Content-Type"] = "application/json";
  }
  if (auth) {
    const token = localStorage.getItem("bisbuddy_token");
    if (token) headers["Authorization"] = `Bearer ${token}`;
  }
  const res = await fetch(`${BASE}${path}`, { ...rest, headers });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail =
        typeof body.detail === "string"
          ? body.detail
          : body.detail
          ? JSON.stringify(body.detail)
          : detail;
    } catch {
      /* keep statusText */
    }
    if (res.status === 401 && !path.includes("/auth/")) {
      localStorage.removeItem("bisbuddy_token");
      localStorage.removeItem("bisbuddy_user");
      window.location.href = "/login";
    }
    throw new ApiError(res.status, detail);
  }
  return res.json();
}

export const api = {
  // ---- auth ---------------------------------------------------------------
  register: (name: string, email: string, password: string) =>
    request<{ access_token: string; user: UserInfo }>("/api/auth/register", {
      method: "POST",
      body: JSON.stringify({ name, email, password }),
      auth: false,
    }),
  login: (email: string, password: string) =>
    request<{ access_token: string; user: UserInfo }>("/api/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
      auth: false,
    }),
  me: () => request<UserInfo>("/api/auth/me"),

  // ---- chat ---------------------------------------------------------------
  chat: (message: string, conversationId: number | null, mode: string) =>
    request<ChatResponse>("/api/chat", {
      method: "POST",
      body: JSON.stringify({
        message,
        conversation_id: conversationId,
        mode,
      }),
    }),
  conversations: (q?: string) =>
    request<ConversationSummary[]>(
      `/api/conversations${q ? `?q=${encodeURIComponent(q)}` : ""}`
    ),
  conversation: (id: number) =>
    request<ConversationDetail>(`/api/conversations/${id}`),
  deleteConversation: (id: number) =>
    request<{ ok: boolean }>(`/api/conversations/${id}`, { method: "DELETE" }),

  // ---- documents ------------------------------------------------------------
  documents: (q?: string, status?: string) => {
    const params = new URLSearchParams();
    if (q) params.set("q", q);
    if (status) params.set("status_filter", status);
    return request<DocumentOut[]>(`/api/documents?${params.toString()}`);
  },
  document: (id: number) => request<DocumentOut>(`/api/documents/${id}`),
  documentFileUrl: (id: number, page?: number) =>
    `${BASE}/api/documents/${id}/file${page ? `?page=${page}` : ""}`,
  uploadDocument: (form: FormData) =>
    request<DocumentOut>("/api/documents/upload", {
      method: "POST",
      body: form,
    }),
  deleteDocument: (id: number) =>
    request<{ ok: boolean }>(`/api/documents/${id}`, { method: "DELETE" }),
  reindexDocument: (id: number) =>
    request<DocumentOut>(`/api/documents/${id}/reindex`, { method: "POST" }),

  // ---- search -----------------------------------------------------------------
  semanticSearch: (q: string, topK = 8, category?: string) => {
    const params = new URLSearchParams({ q, top_k: String(topK) });
    if (category) params.set("category", category);
    return request<{ query: string; results: SearchHit[] }>(
      `/api/search?${params.toString()}`
    );
  },
  documentSearch: (q?: string, category?: string, documentType?: string) => {
    const params = new URLSearchParams();
    if (q) params.set("q", q);
    if (category) params.set("category", category);
    if (documentType) params.set("document_type", documentType);
    return request<DocumentOut[]>(
      `/api/search/documents?${params.toString()}`
    );
  },

  // ---- knowledge base ---------------------------------------------------------
  categories: () =>
    request<KnowledgeCategory[]>("/api/knowledge/categories"),
  products: (category?: string, q?: string) => {
    const params = new URLSearchParams();
    if (category) params.set("category", category);
    if (q) params.set("q", q);
    return request<ProductSummary[]>(`/api/knowledge/products?${params.toString()}`);
  },
  product: (id: number) => request<ProductDetail>(`/api/knowledge/products/${id}`),
  knowledgeStats: () => request<KnowledgeStats>("/api/knowledge/stats"),
  ragDebug: (q: string) =>
    request<RagDebugTrace>(
      `/api/knowledge/debug/retrieval?q=${encodeURIComponent(q)}`
    ),

  // ---- misc ---------------------------------------------------------------
  feedback: (messageId: number, rating: 1 | -1, comment = "") =>
    request<{ id: number }>("/api/feedback", {
      method: "POST",
      body: JSON.stringify({ message_id: messageId, rating, comment }),
    }),
  adminStats: () => request<AdminStats>("/api/admin/stats"),
  publicConfig: () =>
    request<{ llm_provider: string; embedding_provider: string }>(
      "/api/config"
    ),
};

/** Stream chat via SSE. Calls onDelta with each text piece; resolves with final payload. */
export async function streamChat(
  payload: {
    message: string;
    conversation_id: number | null;
    mode: string;
    category?: string | null;
  },
  handlers: {
    onMeta?: (meta: {
      conversation_id: number;
      llm_provider: string;
      detected_category?: string;
      category_label?: string;
      language?: string;
    }) => void;
    onDelta: (text: string) => void;
    onDone: (final: {
      conversation_id: number;
      message_id: number;
      sources: Citation[];
      detected_category?: string;
      category_label?: string;
      related_questions?: string[];
      language?: string;
    }) => void;
    onError?: (message: string) => void;
  }
): Promise<void> {
  const token = localStorage.getItem("bisbuddy_token");
  const res = await fetch(`${BASE}/api/chat/stream`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: JSON.stringify(payload),
  });
  if (!res.ok || !res.body) {
    let detail = res.statusText;
    try {
      detail = (await res.json()).detail ?? detail;
    } catch {
      /* noop */
    }
    handlers.onError?.(detail);
    return;
  }
  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  for (;;) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const parts = buffer.split("\n\n");
    buffer = parts.pop() ?? "";
    for (const part of parts) {
      const eventLine = part
        .split("\n")
        .find((l) => l.startsWith("event:"));
      const dataLine = part.split("\n").find((l) => l.startsWith("data:"));
      if (!dataLine) continue;
      const event = eventLine?.slice(6).trim() ?? "message";
      const data = JSON.parse(dataLine.slice(5).trim());
      if (event === "meta") handlers.onMeta?.(data);
      else if (event === "delta") handlers.onDelta(data.text);
      else if (event === "done") handlers.onDone(data);
      else if (event === "error") handlers.onError?.(data.message);
    }
  }
}
