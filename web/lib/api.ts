import type { Brief, RunResponse, Stats } from "./types";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

/** Raised for any non-OK API response, with a user-friendly message. */
export class ApiError extends Error {
  status: number;
  constructor(message: string, status: number) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

async function parseError(res: Response): Promise<string> {
  if (res.status === 429) {
    return "Rate limit reached (10 runs/minute). Give it a minute and try again.";
  }
  try {
    const data = await res.json();
    if (data?.detail) return String(data.detail);
  } catch {
    /* fall through to generic */
  }
  return `Request failed (${res.status}).`;
}

export async function getStats(): Promise<Stats> {
  const res = await fetch(`${API_URL}/stats`, { cache: "no-store" });
  if (!res.ok) throw new ApiError(await parseError(res), res.status);
  return res.json();
}

export async function runAgent(brief: Brief): Promise<RunResponse> {
  let res: Response;
  try {
    res = await fetch(`${API_URL}/run`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(brief),
    });
  } catch {
    // Network / CORS / backend down.
    throw new ApiError(
      "Could not reach the backend. Is the API running and NEXT_PUBLIC_API_URL set correctly?",
      0,
    );
  }
  if (!res.ok) throw new ApiError(await parseError(res), res.status);
  return res.json();
}

export { API_URL };
