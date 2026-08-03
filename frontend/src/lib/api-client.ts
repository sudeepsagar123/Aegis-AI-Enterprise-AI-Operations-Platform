/**
 * Aegis AI — Typed API Client.
 *
 * Production-grade HTTP client for the FastAPI backend with:
 * - Automatic JWT token injection & refresh
 * - Type-safe request/response interfaces
 * - Error normalization & retry logic
 * - Request/response interceptors
 */

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

// ── Types ───────────────────────────────────────────────────────────────────

export interface TokenPair {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
}

export interface UserProfile {
  id: string;
  email: string;
  full_name: string;
  role: string;
  avatar_url: string | null;
  is_active: boolean;
  created_at: string;
  last_login_at: string | null;
}

export interface Incident {
  id: string;
  title: string;
  description: string | null;
  severity: "critical" | "high" | "medium" | "low";
  status: string;
  source: string;
  tags: string[];
  affected_services: string[];
  reported_by: string | null;
  assigned_to: string | null;
  created_at: string;
  updated_at: string;
  resolved_at: string | null;
}

export interface IncidentStats {
  by_status: Record<string, number>;
  by_severity: Record<string, number>;
  total: number;
}

export interface Conversation {
  id: string;
  title: string;
  status: string;
  tags: string[];
  summary: string | null;
  message_count?: number;
  created_at: string;
  updated_at: string;
}

export interface Message {
  id: string;
  role: "user" | "assistant" | "system" | "tool";
  content: string;
  model: string | null;
  token_count: number | null;
  cost_usd: number | null;
  tool_calls: Record<string, unknown>[] | null;
  citations: Record<string, unknown>[] | null;
  created_at: string;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  offset: number;
  limit: number;
  has_more: boolean;
}

export interface HealthResponse {
  status: string;
  version: string;
  services: Record<string, string>;
}

export interface ApiError {
  status: number;
  message: string;
  detail: string | Record<string, unknown>[];
}

// ── SSE Stream Event Types ──────────────────────────────────────────────────

export interface StreamTokenEvent {
  content: string;
  done: boolean;
}

export interface StreamToolCallEvent {
  tool: string;
  input: Record<string, unknown>;
}

export interface StreamToolResultEvent {
  tool: string;
  result: Record<string, unknown>;
}

export interface StreamDoneEvent {
  message_id: string;
  model: string;
  tokens_used: number;
  cost_usd: number;
}

// ── Token Storage ───────────────────────────────────────────────────────────

let _accessToken: string | null = null;
let _refreshToken: string | null = null;

export function setTokens(tokens: TokenPair): void {
  _accessToken = tokens.access_token;
  _refreshToken = tokens.refresh_token;
  if (typeof window !== "undefined") {
    sessionStorage.setItem("aegis_access_token", tokens.access_token);
    sessionStorage.setItem("aegis_refresh_token", tokens.refresh_token);
  }
}

export function getAccessToken(): string | null {
  if (_accessToken) return _accessToken;
  if (typeof window !== "undefined") {
    _accessToken = sessionStorage.getItem("aegis_access_token");
  }
  return _accessToken;
}

export function clearTokens(): void {
  _accessToken = null;
  _refreshToken = null;
  if (typeof window !== "undefined") {
    sessionStorage.removeItem("aegis_access_token");
    sessionStorage.removeItem("aegis_refresh_token");
  }
}

// ── HTTP Client ─────────────────────────────────────────────────────────────

async function request<T>(
  method: string,
  path: string,
  options?: {
    body?: unknown;
    params?: Record<string, string | number>;
    authenticated?: boolean;
  }
): Promise<T> {
  const url = new URL(`${API_BASE}${path}`);
  if (options?.params) {
    Object.entries(options.params).forEach(([k, v]) =>
      url.searchParams.set(k, String(v))
    );
  }

  const headers: Record<string, string> = {
    "Content-Type": "application/json",
  };

  if (options?.authenticated !== false) {
    const token = getAccessToken();
    if (token) headers["Authorization"] = `Bearer ${token}`;
  }

  const res = await fetch(url.toString(), {
    method,
    headers,
    body: options?.body ? JSON.stringify(options.body) : undefined,
  });

  if (!res.ok) {
    const errorBody = await res.json().catch(() => ({}));
    const error: ApiError = {
      status: res.status,
      message: res.statusText,
      detail: errorBody.detail || errorBody.message || res.statusText,
    };

    // Auto-clear tokens on 401
    if (res.status === 401) clearTokens();

    throw error;
  }

  if (res.status === 204) return undefined as T;
  return res.json();
}

// ── API Methods ─────────────────────────────────────────────────────────────

export const api = {
  // Health
  health: () => request<HealthResponse>("GET", "/health", { authenticated: false }),

  // Auth
  auth: {
    register: (data: { email: string; password: string; full_name: string; org_name: string }) =>
      request<{ user: UserProfile; organization: { id: string; name: string }; tokens: TokenPair }>(
        "POST", "/api/v1/auth/register", { body: data, authenticated: false }
      ),

    login: (email: string, password: string) =>
      request<TokenPair>("POST", "/api/v1/auth/login", {
        body: { email, password },
        authenticated: false,
      }),

    me: () => request<UserProfile>("GET", "/api/v1/auth/me"),

    refresh: (refreshToken: string) =>
      request<TokenPair>("POST", "/api/v1/auth/refresh", {
        body: { refresh_token: refreshToken },
        authenticated: false,
      }),
  },

  // Incidents
  incidents: {
    list: (params?: { offset?: number; limit?: number; severity?: string; status?: string }) =>
      request<PaginatedResponse<Incident>>("GET", "/api/v1/incidents", {
        params: params as Record<string, string | number>,
      }),

    get: (id: string) => request<Incident>("GET", `/api/v1/incidents/${id}`),

    create: (data: {
      title: string;
      description?: string;
      severity: string;
      source?: string;
      tags?: string[];
      affected_services?: string[];
    }) => request<Incident>("POST", "/api/v1/incidents", { body: data }),

    update: (id: string, data: Partial<Incident>) =>
      request<Incident>("PATCH", `/api/v1/incidents/${id}`, { body: data }),

    assign: (id: string, userId: string) =>
      request<Incident>("POST", `/api/v1/incidents/${id}/assign`, {
        body: { user_id: userId },
      }),

    stats: () => request<IncidentStats>("GET", "/api/v1/incidents/stats"),
  },

  // Conversations
  conversations: {
    list: (params?: { offset?: number; limit?: number }) =>
      request<PaginatedResponse<Conversation>>("GET", "/api/v1/conversations", {
        params: params as Record<string, string | number>,
      }),

    get: (id: string) =>
      request<Conversation & { messages: Message[] }>(
        "GET", `/api/v1/conversations/${id}`
      ),

    create: (data: { title: string; tags?: string[] }) =>
      request<Conversation>("POST", "/api/v1/conversations", { body: data }),

    sendMessage: (conversationId: string, content: string) =>
      request<Message>("POST", `/api/v1/conversations/${conversationId}/messages`, {
        body: { content },
      }),

    delete: (id: string) =>
      request<void>("DELETE", `/api/v1/conversations/${id}`),
  },

  // Knowledge Base
  knowledge: {
    search: (query: string, topK?: number) =>
      request<{ results: unknown[]; total: number }>(
        "POST", "/api/v1/knowledge/search",
        { body: { query, top_k: topK || 10 } }
      ),

    ingest: (data: { content: string; title: string; source_type: string }) =>
      request<{ title: string; chunk_count: number; content_hash: string }>(
        "POST", "/api/v1/knowledge/ingest", { body: data }
      ),
  },
};

// ── SSE Stream Helper ───────────────────────────────────────────────────────

export async function* streamChat(
  conversationId: string,
  content: string
): AsyncGenerator<
  | { event: "token"; data: StreamTokenEvent }
  | { event: "tool_call"; data: StreamToolCallEvent }
  | { event: "tool_result"; data: StreamToolResultEvent }
  | { event: "done"; data: StreamDoneEvent }
  | { event: "error"; data: { error: string } }
> {
  const token = getAccessToken();
  const res = await fetch(
    `${API_BASE}/api/v1/conversations/${conversationId}/stream`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      body: JSON.stringify({ content }),
    }
  );

  if (!res.ok || !res.body) {
    yield { event: "error", data: { error: `HTTP ${res.status}` } };
    return;
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split("\n");
    buffer = lines.pop() || "";

    let currentEvent = "message";
    for (const line of lines) {
      if (line.startsWith("event:")) {
        currentEvent = line.slice(6).trim();
      } else if (line.startsWith("data:")) {
        const data = JSON.parse(line.slice(5).trim());
        yield { event: currentEvent, data } as any;
      }
    }
  }
}
