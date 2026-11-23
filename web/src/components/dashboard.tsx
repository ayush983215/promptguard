"use client";

import { useCallback, useEffect, useState } from "react";
import { RefreshCw, TriangleAlert } from "lucide-react";

import { DecisionBadge, DECISION, TYPE_LABEL } from "@/components/decision-badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import type { Action, EventRow, Stats } from "@/lib/types";

const REFRESH_MS = 15_000;
const ORDER: Action[] = ["block", "redact", "warn", "allow"];

export function Dashboard() {
  const [stats, setStats] = useState<Stats | null>(null);
  const [events, setEvents] = useState<EventRow[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [updated, setUpdated] = useState<Date | null>(null);
  const [busy, setBusy] = useState(false);

  // A pure request (no state changes), then small callbacks that apply the result.
  const request = useCallback(async (): Promise<[Stats, EventRow[]]> => {
    const [s, e] = await Promise.all([fetch("/api/stats"), fetch("/api/events")]);
    if (!s.ok || !e.ok) throw new Error("Dashboard data is unavailable. Check that the guard service is running and its admin token is set.");
    return [await s.json(), await e.json()];
  }, []);
  const onData = useCallback(([s, e]: [Stats, EventRow[]]) => {
    setStats(s);
    setEvents(e);
    setError(null);
    setUpdated(new Date());
  }, []);
  const onError = useCallback((err: unknown) => {
    setError(err instanceof Error ? err.message : "Dashboard data is unavailable.");
  }, []);

  // Refresh button: also shows a spinner while it runs.
  const load = useCallback(async () => {
    setBusy(true);
    try {
      onData(await request());
    } catch (err) {
      onError(err);
    } finally {
      setBusy(false);
    }
  }, [request, onData, onError]);

  // Initial load and polling every 15 s.
  useEffect(() => {
    const run = () => request().then(onData, onError);
    run();
    const id = setInterval(run, REFRESH_MS);
    return () => clearInterval(id);
  }, [request, onData, onError]);

  const refresh = (
    <div className="flex items-center gap-3">
      <span className="text-xs text-muted-foreground" aria-live="polite">
        {updated ? `Updated ${updated.toLocaleTimeString()}` : "Loading"}
      </span>
      <Button type="button" variant="outline" onClick={load} disabled={busy}>
        <RefreshCw className={busy ? "animate-spin" : undefined} aria-hidden="true" />
        Refresh
      </Button>
    </div>
  );

  if (error && !stats) {
    return (
      <div className="space-y-4">
        <div role="alert" className="flex gap-3 rounded-xl border border-block/30 bg-block-soft p-4 text-sm text-block-fg">
          <TriangleAlert className="mt-0.5 size-4 shrink-0" aria-hidden="true" />
          <p>{error}</p>
        </div>
        {refresh}
      </div>
    );
  }
  if (!stats || !events) return <DashboardSkeleton />;

  const total = Object.values(stats.decisions).reduce((a, b) => a + (b ?? 0), 0);
  const decisionItems = ORDER.map((a) => ({ key: a, label: DECISION[a].label, count: stats.decisions[a] ?? 0, bar: DECISION[a].bar }));
  const typeItems = stats.top_types.map(([t, n]) => ({ key: t, label: TYPE_LABEL(t), count: n, bar: "bg-primary" }));

  return (
    <div className="space-y-6">
      <div className="flex justify-end">{refresh}</div>
      {error && (
        <p role="alert" className="text-sm text-block-fg">
          Could not refresh just now. Showing the last data received.
        </p>
      )}

      <section aria-label="Key numbers" className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <Kpi label="Prompts checked" value={total} hint="all time" />
        <Kpi label="Blocked" value={stats.decisions.block ?? 0} hint="nothing sent" tone="block" />
        <Kpi label="Redacted" value={stats.decisions.redact ?? 0} hint="values removed" tone="redact" />
        <Kpi label="AI overrides refused" value={stats.agent_loosen_attempts_blocked} hint="advisor tried to loosen a rule" />
      </section>

      <div className="grid gap-4 lg:grid-cols-3">
        <Panel title="Decisions" description="What happened to each prompt">
          <BarList items={decisionItems} empty="No prompts checked yet." />
        </Panel>
        <Panel title="Most common leak types" description="What people tried to send">
          <BarList items={typeItems} empty="No findings yet." />
        </Panel>
        <Panel title="Repeated values" description="The same secret seen more than once">
          {stats.repeated_values.length === 0 ? (
            <p className="text-sm text-muted-foreground">Nothing repeated yet.</p>
          ) : (
            <ul className="space-y-2 text-sm">
              {stats.repeated_values.map(([type, n], i) => (
                <li key={i} className="flex items-center justify-between rounded-lg border px-3 py-2">
                  <span>{TYPE_LABEL(type)}</span>
                  <span className="tabular-nums text-muted-foreground">{n} times</span>
                </li>
              ))}
            </ul>
          )}
          <p className="mt-3 text-xs leading-relaxed text-muted-foreground">
            Matched by a keyed hash, so the value itself is never stored.
          </p>
        </Panel>
      </div>

      <Panel title="Recent activity" description="Newest first. Prompt text is never stored, only what was found.">
        {events.length === 0 ? (
          <p className="text-sm text-muted-foreground">No activity yet. Check a prompt in the Playground.</p>
        ) : (
          <div className="rounded-lg border">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Time</TableHead>
                  <TableHead>User</TableHead>
                  <TableHead>Decision</TableHead>
                  <TableHead>Found</TableHead>
                  <TableHead className="text-right">Chars</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {events.map((ev) => (
                  <TableRow key={ev.id}>
                    <TableCell className="whitespace-nowrap tabular-nums text-muted-foreground">
                      {new Date(ev.ts * 1000).toLocaleString([], { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit", second: "2-digit" })}
                    </TableCell>
                    <TableCell>{ev.user}</TableCell>
                    <TableCell>
                      <DecisionBadge action={ev.decision} />
                    </TableCell>
                    <TableCell>
                      {ev.findings.length === 0 ? (
                        <span className="text-muted-foreground">Nothing</span>
                      ) : (
                        <span className="flex flex-wrap gap-1">
                          {ev.findings.map((f, i) => (
                            <span key={i} className="rounded-md border bg-muted/60 px-1.5 py-0.5 text-xs">
                              {TYPE_LABEL(f.type)}
                            </span>
                          ))}
                        </span>
                      )}
                    </TableCell>
                    <TableCell className="text-right tabular-nums text-muted-foreground">{ev.prompt_chars.toLocaleString()}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        )}
      </Panel>
    </div>
  );
}

function Kpi({ label, value, hint, tone }: { label: string; value: number; hint: string; tone?: Action }) {
  return (
    <Card size="sm" className="transition-shadow hover:shadow-md">
      <CardContent>
        <p className="text-xs font-medium text-muted-foreground">{label}</p>
        <p className="mt-1 flex items-center gap-2 text-3xl font-semibold tabular-nums tracking-tight">
          {value.toLocaleString()}
          {tone && <span aria-hidden="true" className={`size-2.5 rounded-full ${DECISION[tone].bar}`} />}
        </p>
        <p className="mt-1 text-xs text-muted-foreground">{hint}</p>
      </CardContent>
    </Card>
  );
}

function Panel({ title, description, children }: { title: string; description: string; children: React.ReactNode }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">{title}</CardTitle>
        <CardDescription>{description}</CardDescription>
      </CardHeader>
      <CardContent>{children}</CardContent>
    </Card>
  );
}

/** Horizontal bars. Every bar also prints its number, so meaning never depends on colour or length alone. */
function BarList({ items, empty }: { items: { key: string; label: string; count: number; bar: string }[]; empty: string }) {
  const max = Math.max(1, ...items.map((i) => i.count));
  if (items.every((i) => i.count === 0)) return <p className="text-sm text-muted-foreground">{empty}</p>;
  return (
    <ul className="space-y-3">
      {items.map((i) => (
        <li key={i.key}>
          <div className="mb-1 flex items-baseline justify-between text-sm">
            <span>{i.label}</span>
            <span className="tabular-nums text-muted-foreground">{i.count}</span>
          </div>
          <div className="h-2 overflow-hidden rounded-full bg-muted" aria-hidden="true">
            <div className={`h-full rounded-full ${i.bar}`} style={{ width: `${(i.count / max) * 100}%` }} />
          </div>
        </li>
      ))}
    </ul>
  );
}

function DashboardSkeleton() {
  return (
    <div className="animate-pulse space-y-6" role="status" aria-label="Loading dashboard">
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        {[0, 1, 2, 3].map((i) => (
          <div key={i} className="h-24 rounded-xl bg-muted" />
        ))}
      </div>
      <div className="grid gap-4 lg:grid-cols-3">
        {[0, 1, 2].map((i) => (
          <div key={i} className="h-56 rounded-xl bg-muted" />
        ))}
      </div>
      <div className="h-64 rounded-xl bg-muted" />
    </div>
  );
}
