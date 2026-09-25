"use client";
import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { ArrowRight, Bookmark, PenLine, ScanLine, Sparkles } from "lucide-react";
import { api } from "@/lib/api";
import { keys, useMe } from "@/lib/queries";
import { AnalysisRow } from "@/components/analysis/analysis-row";
import { VERDICT_META } from "@/components/analysis/verdict";
import { QueryError } from "@/components/query-error";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { EmptyState } from "@/components/ui/empty-state";
import { Skeleton } from "@/components/ui/skeleton";
import type { Verdict } from "@/lib/types";

function greeting() {
  const h = new Date().getHours();
  return h < 12 ? "Good morning" : h < 18 ? "Good afternoon" : "Good evening";
}

export default function DashboardPage() {
  const me = useMe();
  const q = useQuery({ queryKey: keys.dashboard, queryFn: api.dashboard });
  const firstName = me.data?.full_name?.split(" ")[0];
  const d = q.data;
  const total = d ? d.verdict_counts.GREEN + d.verdict_counts.YELLOW + d.verdict_counts.RED : 0;

  return (
    <div className="space-y-6">
      <div>
        <p className="text-sm text-muted">{greeting()}{firstName ? `, ${firstName}` : ""}</p>
        <h1 className="mt-1 text-2xl font-bold tracking-tight sm:text-3xl">What are you eating today?</h1>
      </div>

      <Link
        href="/scan"
        className="group relative flex items-center gap-5 overflow-hidden rounded-3xl bg-primary p-6 text-primary-foreground shadow-card sm:p-8"
      >
        <div aria-hidden className="absolute -right-10 -top-10 size-48 rounded-full bg-accent/30 blur-2xl" />
        <span className="relative grid size-14 shrink-0 place-items-center rounded-2xl bg-accent text-accent-foreground">
          <ScanLine className="size-7" aria-hidden />
        </span>
        <span className="relative flex-1">
          <span className="block text-xl font-semibold sm:text-2xl">Scan a product</span>
          <span className="mt-0.5 block text-sm opacity-80">Camera or photo upload · results in seconds</span>
        </span>
        <ArrowRight className="relative size-5 transition-transform group-hover:translate-x-1" aria-hidden />
      </Link>

      <div className="grid grid-cols-2 gap-3 sm:max-w-md">
        <Button asChild variant="outline" className="h-auto justify-start gap-3 rounded-2xl p-4">
          <Link href="/analyze"><PenLine /> Type ingredients</Link>
        </Button>
        <Button asChild variant="outline" className="h-auto justify-start gap-3 rounded-2xl p-4">
          <Link href="/saved"><Bookmark /> Saved</Link>
        </Button>
      </div>

      {q.isError ? (
        <QueryError error={q.error} onRetry={() => q.refetch()} />
      ) : (
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 sm:gap-4">
          <Card>
            <CardContent className="pt-5 sm:pt-6">
              <p className="text-sm text-muted">Products analyzed</p>
              {d ? <p className="mt-1 text-3xl font-bold tabular" data-testid="stat-total">{d.total_analyses}</p> : <Skeleton className="mt-2 h-9 w-16" />}
            </CardContent>
          </Card>
          <Card>
            <CardContent className="pt-5 sm:pt-6">
              <p className="text-sm text-muted">Average score</p>
              {d ? <p className="mt-1 text-3xl font-bold tabular">{d.average_score ?? "—"}</p> : <Skeleton className="mt-2 h-9 w-16" />}
            </CardContent>
          </Card>
          <Card className="col-span-2 sm:col-span-1">
            <CardContent className="pt-5 sm:pt-6">
              <p className="text-sm text-muted">Verdicts</p>
              {d ? (
                <>
                  <div className="mt-3 flex h-2.5 overflow-hidden rounded-full bg-surface-2" aria-hidden>
                    {(["GREEN", "YELLOW", "RED"] as Verdict[]).map((v) =>
                      d.verdict_counts[v] ? (
                        <div key={v} style={{ width: `${(d.verdict_counts[v] / total) * 100}%`, background: VERDICT_META[v].stroke }} />
                      ) : null,
                    )}
                  </div>
                  <ul className="mt-2 flex gap-3 text-xs text-muted">
                    {(["GREEN", "YELLOW", "RED"] as Verdict[]).map((v) => (
                      <li key={v}><span className="font-semibold text-foreground tabular">{d.verdict_counts[v]}</span> {VERDICT_META[v].label.toLowerCase()}</li>
                    ))}
                  </ul>
                </>
              ) : <Skeleton className="mt-3 h-6 w-full" />}
            </CardContent>
          </Card>
        </div>
      )}

      <Card>
        <CardHeader className="flex-row items-center justify-between">
          <CardTitle>Recent analyses</CardTitle>
          {d && d.recent.length > 0 && (
            <Button asChild variant="link" size="sm"><Link href="/history">View all</Link></Button>
          )}
        </CardHeader>
        <CardContent>
          {!d ? (
            <div className="space-y-2">{[0, 1, 2].map((i) => <Skeleton key={i} className="h-16" />)}</div>
          ) : d.recent.length === 0 ? (
            <EmptyState
              icon={<Sparkles />}
              title="No analyses yet"
              description="Scan your first product or try one of our example ingredient lists."
              action={<Button asChild><Link href="/analyze">Try an example</Link></Button>}
            />
          ) : (
            <ul className="space-y-2">{d.recent.map((a) => <li key={a.id}><AnalysisRow a={a} /></li>)}</ul>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
