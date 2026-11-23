import { backend, relay } from "@/lib/backend";

const MAX_CHARS = 100_000;

export async function POST(request: Request) {
  let body: unknown;
  try {
    body = await request.json();
  } catch {
    return Response.json({ error: "Body must be JSON." }, { status: 400 });
  }
  const prompt = (body as { prompt?: unknown })?.prompt;
  if (typeof prompt !== "string" || prompt.trim() === "") {
    return Response.json({ error: "Enter a prompt to check." }, { status: 400 });
  }
  if (prompt.length > MAX_CHARS) {
    return Response.json({ error: `Prompt is longer than ${MAX_CHARS.toLocaleString()} characters.` }, { status: 413 });
  }
  // The visitor can not choose the audit identity: it is fixed server-side.
  return relay(() => backend("/check", { method: "POST", body: JSON.stringify({ prompt, user: "web-visitor" }) }));
}
