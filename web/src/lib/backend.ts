/**
 * Server-side helper for talking to the PromptGuard (FastAPI) service.
 * Only route handlers import this, so the admin token never reaches the browser.
 */
const BASE = (process.env.PROMPTGUARD_API ?? "http://127.0.0.1:8000").replace(/\/$/, "");

export async function backend(path: string, init: RequestInit = {}, admin = false): Promise<Response> {
  const headers = new Headers(init.headers);
  if (init.body) headers.set("content-type", "application/json");
  if (admin) headers.set("x-admin-token", process.env.PG_ADMIN_TOKEN ?? "");
  return fetch(`${BASE}${path}`, {
    ...init,
    headers,
    cache: "no-store",
    signal: AbortSignal.timeout(8000),
  });
}

/** Forward a backend response, or return a generic 502 so internal details are not leaked. */
export async function relay(call: () => Promise<Response>): Promise<Response> {
  try {
    const res = await call();
    if (!res.ok) return Response.json({ error: "The guard service rejected the request." }, { status: res.status === 403 ? 502 : res.status });
    return Response.json(await res.json());
  } catch {
    return Response.json({ error: "The guard service is unreachable." }, { status: 502 });
  }
}
