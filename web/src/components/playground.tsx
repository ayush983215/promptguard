"use client";

import { useEffect, useRef, useState } from "react";
import { Info, Loader2, ScanSearch, TriangleAlert } from "lucide-react";

import { DecisionBadge, DECISION, TYPE_LABEL } from "@/components/decision-badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Textarea } from "@/components/ui/textarea";
import type { CheckResult, Example } from "@/lib/types";

const MAX_CHARS = 100_000;

export function Playground() {
  const [prompt, setPrompt] = useState("");
  const [examples, setExamples] = useState<Example[]>([]);
  const [result, setResult] = useState<CheckResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const resultRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    fetch("/api/examples")
      .then((r) => (r.ok ? r.json() : []))
      .then((list: Example[]) => setExamples(Array.isArray(list) ? list : []))
      .catch(() => setExamples([]));
  }, []);

  async function check() {
    if (!prompt.trim() || loading) return;
    setLoading(true);
    setError(null);
    try {
      const res = await fetch("/api/check", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ prompt }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data?.error ?? "Something went wrong.");
      setResult(data as CheckResult);
      resultRef.current?.focus({ preventScroll: false });
    } catch (e) {
      setResult(null);
      setError(e instanceof Error ? e.message : "Something went wrong.");
    } finally {
      setLoading(false);
    }
  }

  function clear() {
    setPrompt("");
    setResult(null);
    setError(null);
  }

  return (
    <div className="space-y-6">
      <div
        role="note"
        className="flex gap-3 rounded-xl border border-warn/30 bg-warn-soft p-4 text-sm leading-relaxed text-warn-fg"
      >
        <Info className="mt-0.5 size-4 shrink-0" aria-hidden="true" />
        <p>
          <strong className="font-semibold">Demo only.</strong> Do not paste real secrets or personal data. Use the placeholder
          examples below. Only masked previews are kept in the audit log.
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Prompt to check</CardTitle>
          <CardDescription>Write what an employee might paste into an AI tool, or start from an example.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {examples.length > 0 && (
            <div role="group" aria-label="Example prompts" className="flex flex-wrap gap-2">
              {examples.map((ex) => (
                <Button key={ex.label} type="button" variant="outline" size="sm" onClick={() => setPrompt(ex.prompt)}>
                  {ex.label}
                </Button>
              ))}
            </div>
          )}

          <div>
            <label htmlFor="prompt" className="mb-1.5 block text-sm font-medium">
              Prompt
            </label>
            <Textarea
              id="prompt"
              value={prompt}
              maxLength={MAX_CHARS}
              onChange={(e) => setPrompt(e.target.value)}
              onKeyDown={(e) => {
                if ((e.metaKey || e.ctrlKey) && e.key === "Enter") check();
              }}
              placeholder="e.g. Why is erp-db01.corp at 10.20.30.40 timing out? Ask priya.sharma@acme-corp.com"
              className="min-h-32 font-mono text-sm"
              aria-describedby="prompt-help"
            />
            <p id="prompt-help" className="mt-1.5 text-xs text-muted-foreground">
              {prompt.length.toLocaleString()} / {MAX_CHARS.toLocaleString()} characters. Press Ctrl or Cmd + Enter to check.
            </p>
          </div>

          <div className="flex flex-wrap gap-2">
            <Button type="button" onClick={check} disabled={loading || !prompt.trim()} size="lg">
              {loading ? <Loader2 className="animate-spin" aria-hidden="true" /> : <ScanSearch aria-hidden="true" />}
              {loading ? "Checking" : "Check prompt"}
            </Button>
            <Button type="button" variant="ghost" size="lg" onClick={clear} disabled={loading || (!prompt && !result && !error)}>
              Clear
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Results are announced to screen readers when they change. */}
      <div ref={resultRef} tabIndex={-1} aria-live="polite" className="outline-none">
        {error && (
          <div role="alert" className="flex gap-3 rounded-xl border border-block/30 bg-block-soft p-4 text-sm text-block-fg">
            <TriangleAlert className="mt-0.5 size-4 shrink-0" aria-hidden="true" />
            <p>{error}</p>
          </div>
        )}

        {!error && !result && (
          <Card className="border-dashed bg-transparent shadow-none ring-0 border">
            <CardContent className="py-8 text-center text-sm text-muted-foreground">
              No result yet. Choose an example or paste a prompt, then select <strong>Check prompt</strong>.
            </CardContent>
          </Card>
        )}

        {result && <ResultCard result={result} />}
      </div>
    </div>
  );
}

function ResultCard({ result }: { result: CheckResult }) {
  const d = DECISION[result.decision];
  const tightened = result.agent.tightened;
  return (
    <Card>
      <CardHeader>
        <div className="flex flex-wrap items-center gap-3">
          <DecisionBadge action={result.decision} size="lg" />
          <span className="text-sm text-muted-foreground">{d.meaning}</span>
        </div>
        <CardDescription className="pt-1 text-sm leading-relaxed text-foreground">{result.explanation}</CardDescription>
      </CardHeader>

      <CardContent className="grid grid-cols-[minmax(0,1fr)] gap-6 lg:grid-cols-2">
        <section aria-labelledby="forwarded" className="min-w-0">
          <h2 id="forwarded" className="mb-2 text-sm font-medium">
            Forwarded to the AI tool
          </h2>
          {result.text === null ? (
            <p className="rounded-lg border border-dashed p-4 text-sm text-muted-foreground">
              Nothing is forwarded when a prompt is blocked.
            </p>
          ) : (
            <pre className="max-h-64 overflow-auto rounded-lg border bg-muted/50 p-3 font-mono text-xs leading-relaxed break-words whitespace-pre-wrap">
              {result.text}
            </pre>
          )}
        </section>

        <section aria-labelledby="findings" className="min-w-0">
          <h2 id="findings" className="mb-2 text-sm font-medium">
            Findings <span className="font-normal text-muted-foreground">(masked: this is all the audit log keeps)</span>
          </h2>
          {result.findings.length === 0 ? (
            <p className="rounded-lg border border-dashed p-4 text-sm text-muted-foreground">No sensitive data detected.</p>
          ) : (
            <div className="rounded-lg border">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Type</TableHead>
                    <TableHead>Action</TableHead>
                    <TableHead>Confidence</TableHead>
                    <TableHead>Preview</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {result.findings.map((f, i) => (
                    <TableRow key={i}>
                      <TableCell className="font-medium">{TYPE_LABEL(f.type)}</TableCell>
                      <TableCell>
                        <DecisionBadge action={f.action} />
                      </TableCell>
                      <TableCell className="capitalize text-muted-foreground">{f.confidence}</TableCell>
                      <TableCell className="font-mono text-xs">{f.masked}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          )}
        </section>

        <p className="text-xs leading-relaxed text-muted-foreground lg:col-span-2">
          {result.agent.used
            ? tightened
              ? "The AI advisor made this decision stricter than the rules alone. It can never make one weaker."
              : result.agent.loosen_attempt_ignored
                ? "The AI advisor suggested a weaker decision. It was ignored and logged: the rules always win."
                : "The AI advisor reviewed this and kept the rule-based decision."
            : "Decided by the deterministic rules only. The optional AI advisor is switched off in this demo."}
        </p>
      </CardContent>
    </Card>
  );
}
