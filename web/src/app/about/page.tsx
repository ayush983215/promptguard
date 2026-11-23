import type { Metadata } from "next";
import { CheckCircle2, CircleAlert } from "lucide-react";

import { PageHeader } from "@/components/page-header";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

export const metadata: Metadata = { title: "How it works" };

const STEPS = [
  { title: "Detect", body: "Plain code finds API keys, private keys, card numbers (Luhn check), emails, phone numbers, internal IPs and hostnames, and random-looking strings. Encoded secrets are decoded and re-checked." },
  { title: "Apply policy", body: "A YAML file maps each finding type to allow, warn, redact or block. The strongest action wins. A typo in the file stops the service instead of weakening a rule." },
  { title: "Advise (optional)", body: "An AI advisor sees only finding types and masked previews, never the prompt. It can explain a decision or make it stricter. It can never make one weaker." },
  { title: "Log", body: "The audit log stores the type, the action, a masked preview and a keyed hash. It never stores the secret or the prompt." },
];

const PROPERTIES = [
  ["The AI can only tighten", "The final decision is the stricter of the rules and the advisor. A hijacked advisor can over-block but never leak."],
  ["Fails closed", "Errors, oversized prompts and invalid policy all end in block or refusing to start."],
  ["Secrets stay out of logs", "Masked previews plus an HMAC. A plain hash of a phone number could be brute-forced; a keyed one cannot."],
  ["Admin data is locked by default", "The dashboard endpoints need a token. If none is configured they stay closed."],
  ["Look-alike tricks are normalised", "Fullwidth letters are folded and invisible characters such as zero-width spaces are removed before scanning."],
];

const CLOSED = ["Base64 up to three layers deep", "Hex-encoded keys", "Zero-width characters inside a key", "Fullwidth look-alike letters"];
const OPEN = [
  "rot13 or reversed text",
  "A key split across lines or chunks",
  "A key spelled out in words",
  "Names, addresses and free-text business secrets",
  "Anyone who skips the gateway and opens an AI tool directly",
];

export default function AboutPage() {
  return (
    <>
      <PageHeader
        title="How PromptGuard works"
        description="A small, auditable pipeline. The detection is deterministic code, so it can be tested and explained line by line."
      />

      <ol className="grid gap-4 sm:grid-cols-2" aria-label="Pipeline steps">
        {STEPS.map((s, i) => (
          <li key={s.title}>
            <Card className="h-full transition-shadow hover:shadow-md">
              <CardHeader>
                <CardTitle className="flex items-center gap-3 text-base">
                  <span className="grid size-7 place-items-center rounded-full bg-accent text-sm font-semibold text-accent-foreground">{i + 1}</span>
                  {s.title}
                </CardTitle>
              </CardHeader>
              <CardContent className="text-sm leading-relaxed text-muted-foreground">{s.body}</CardContent>
            </Card>
          </li>
        ))}
      </ol>

      <section className="mt-10" aria-labelledby="props">
        <h2 id="props" className="mb-4 text-lg font-semibold tracking-tight">Security properties</h2>
        <dl className="grid gap-3">
          {PROPERTIES.map(([t, d]) => (
            <div key={t} className="rounded-xl border bg-card p-4">
              <dt className="text-sm font-medium">{t}</dt>
              <dd className="mt-1 text-sm leading-relaxed text-muted-foreground">{d}</dd>
            </div>
          ))}
        </dl>
      </section>

      <section className="mt-10" aria-labelledby="limits">
        <h2 id="limits" className="mb-1 text-lg font-semibold tracking-tight">Limits, stated plainly</h2>
        <p className="mb-4 text-sm text-muted-foreground">Evaluated on test cases written by the author, so detection numbers are optimistic.</p>
        <div className="grid gap-4 md:grid-cols-2">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-base text-allow-fg"><CheckCircle2 className="size-4" aria-hidden="true" />Evasions now caught</CardTitle>
              <CardDescription>Each has a regression test.</CardDescription>
            </CardHeader>
            <CardContent>
              <ul className="space-y-2 text-sm">{CLOSED.map((c) => <li key={c}>{c}</li>)}</ul>
            </CardContent>
          </Card>
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-base text-redact-fg"><CircleAlert className="size-4" aria-hidden="true" />Still gets through</CardTitle>
              <CardDescription>Known gaps, listed rather than hidden.</CardDescription>
            </CardHeader>
            <CardContent>
              <ul className="space-y-2 text-sm">{OPEN.map((c) => <li key={c}>{c}</li>)}</ul>
            </CardContent>
          </Card>
        </div>
        <p className="mt-6 text-sm leading-relaxed text-muted-foreground">
          This is a prototype built to understand how data-loss prevention for AI works. Commercial tools such as Microsoft Purview and Netskope
          do this at scale. The biggest real-world gap is enforcement: a gateway only protects traffic that goes through it.
        </p>
      </section>
    </>
  );
}
