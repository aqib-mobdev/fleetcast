import type { AnalyzeInput, Corridor, Health, Place, TripResponse } from "./types";

const BASE = (import.meta.env.VITE_API_BASE_URL as string | undefined)?.replace(/\/$/, "") ?? "";

export class ApiError extends Error {
  readonly code: string;
  readonly field: string | null;
  readonly status: number;

  constructor(message: string, code: string, status: number, field: string | null = null) {
    super(message);
    this.name = "ApiError";
    this.code = code;
    this.field = field;
    this.status = status;
  }
}

async function call<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${BASE}${path}`, {
      ...init,
      headers: { "Content-Type": "application/json", ...(init?.headers ?? {}) },
    });
  } catch {
    throw new ApiError("API is unreachable. Is the backend running?", "network", 0);
  }

  const body = await response.json().catch(() => null);
  if (!response.ok) {
    const error = body?.error;
    throw new ApiError(
      error?.message ?? `Request failed (${response.status})`,
      error?.code ?? "request_failed",
      response.status,
      error?.field ?? null,
    );
  }
  return body as T;
}

export const api = {
  analyze: (input: AnalyzeInput) =>
    call<TripResponse>("/api/trips/analyze", { method: "POST", body: JSON.stringify(input) }),

  corridor: (tripId: string, route: string) =>
    call<Corridor>(`/api/trips/${tripId}/corridor?route=${encodeURIComponent(route)}`),

  places: (query: string) =>
    call<{ places: Place[] }>(`/api/places?q=${encodeURIComponent(query)}`),

  health: () => call<Health>("/api/health"),
};
