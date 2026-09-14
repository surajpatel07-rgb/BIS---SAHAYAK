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
  semanticSearch: (q: string, topK = 8) =>
    request<{ query: string; results: SearchHit[] }>(
      `/api/search?q=${encodeURIComponent(q)}&top_k=${topK}`
    ),
  documentSearch: (q?: string, category?: string, documentType?: string) => {
    const params = new URLSearchParams();
    if (q) params.set("q", q);
    if (category) params.set("category", category);
    if (documentType) params.set("document_type", documentType);
    return request<DocumentOut[]>(
      `/api/search/documents?${params.toString()}`
    );
  },

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
  payload: { message: string; conversation_id: number | null; mode: string },
  handlers: {
    onMeta?: (meta: { conversation_id: number; llm_provider: string }) => void;
    onDelta: (text: string) => void;
    onDone: (final: { conversation_id: number; message_id: number; sources: Citation[] }) => void;
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
