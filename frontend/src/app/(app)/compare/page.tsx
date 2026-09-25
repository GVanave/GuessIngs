"use client";
import Link from "next/link";
import { Suspense, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { GitCompareArrows, Trophy } from "lucide-react";
import { api } from "@/lib/api";
import { keys } from "@/lib/queries";
import type { Analysis } from "@/lib/types";
import { cn, formatPoints } from "@/lib/utils";
import { AnalysisRow } from "@/components/analysis/analysis-row";
import { ScoreRing } from "@/components/analysis/score-ring";
import { VerdictBadge } from "@/components/analysis/verdict";
import { PageHeader } from "@/components/layout/page-header";
import { QueryError } from "@/components/query-error";
import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/empty-state";
import { PageSkeleton, Skeleton } from "@/components/ui/skeleton";

const RULES = [
  ["added_sugar", "Added sugar"], ["artificial_sweetener", "Sweeteners"], ["hydrogenated_oil", "Hydrogenated oil"],
  ["artificial_color", "Artificial colors"], ["artificial_flavor", "Artificial flavors"], ["preservative", "Preservatives"],
  ["emulsifier", "Emulsifiers"], ["sodium", "High sodium"], ["nova4", "NOVA 4"], ["fiber_protein", "Fiber/protein"],
  ["healthy_fat", "Healthy fat"],
] as const;

function pointsFor(a: Analysis, code: string) {
  return a.breakdown.filter((l) => l.code === code).reduce((s, l) => s + l.points, 0);
}

function Picker({ initial }: { initial: string[] }) {
  const router = useRouter();
  const [selected, setSelected] = useState<string[]>(initial);
  const q = useQuery({ queryKey: ["history", { picker: true }], queryFn: () => api.history({ limit: 50 }) });
  const toggle = (id: string) => setSelected((s) => (s.includes(id) ? s.filter((x) => x !== id) : s.length >= 4 ? s : [...s, id]));
  if (q.isError) return <QueryError error={q.error} onRetry={() => q.refetch()} />;
  if (q.isPending) return <div className="space-y-2">{[0, 1, 2].map((i) => <Skeleton key={i} className="h-16" />)}</div>;
  if (q.data.items.length < 2)
    return (
      <EmptyState icon={<GitCompareArrows />} title="Analyze at least two products" description="Once you have two or more analyses, you can compare them side by side."
        action={<Button asChild><Link href="/scan">Scan a product</Link></Button>} />
    );
  return (
    <div>
      <p className="mb-3 text-sm text-muted">Choose 2–4 products to compare.</p>
      <ul className="space-y-2">
        {q.data.items.map((a) => (
          <li key={a.id}><AnalysisRow a={a} selectable selected={selected.includes(a.id)} onToggle={() => toggle(a.id)} /></li>
        ))}
      </ul>
      <div className="sticky bottom-24 mt-4 flex justify-end lg:bottom-6">
        <Button size="lg" disabled={selected.length < 2} onClick={() => router.push(`/compare?${selected.map((i) => `ids=${i}`).join("&")}`)}>
          Compare {selected.length > 0 ? `(${selected.length})` : ""}
        </Button>
      </div>
    </div>
  );
}

function Comparison({ ids }: { ids: string[] }) {
  const q = useQuery({ queryKey: keys.compare(ids), queryFn: () => api.compare(ids) });
  if (q.isPending) return <PageSkeleton />;
  if (q.isError) return <QueryError error={q.error} onRetry={() => q.refetch()} />;
  const { items, best_id, shared_concerns } = q.data;
  return (
    <div className="space-y-5">
      <div className="-mx-4 overflow-x-auto px-4 pb-2 pt-4 sm:mx-0 sm:px-0">
        <div className="grid min-w-max auto-cols-[minmax(220px,1fr)] grid-flow-col gap-3 sm:min-w-0">
          {items.map((a) => (
            <div key={a.id} className={cn("relative flex flex-col items-center rounded-2xl border bg-surface p-5 text-center shadow-card", a.id === best_id ? "border-good ring-2 ring-good/30" : "border-border")}>
              {a.id === best_id && (
                <span className="absolute -top-3 inline-flex items-center gap-1 rounded-full bg-good px-2.5 py-0.5 text-xs font-semibold text-white">
                  <Trophy className="size-3.5" aria-hidden /> Best pick
                </span>
              )}
              <ScoreRing score={a.score} verdict={a.verdict} size={112} />
              <Link href={`/analysis/${a.id}`} className="mt-3 line-clamp-2 font-semibold hover:underline">{a.product.name}</Link>
              <VerdictBadge verdict={a.verdict} size="sm" className="mt-2" />
              <p className="mt-2 text-xs text-muted">{a.concerns.length} to watch · {a.positives.length} positive</p>
            </div>
          ))}
        </div>
      </div>

      <div className="overflow-x-auto rounded-2xl border border-border bg-surface">
        <table className="w-full min-w-[480px] text-sm">
          <caption className="sr-only">Score contributions by rule</caption>
          <thead>
            <tr className="border-b border-border text-left">
              <th scope="col" className="px-4 py-3 font-semibold">Rule</th>
              {items.map((a) => <th key={a.id} scope="col" className="px-4 py-3 text-right font-semibold"><span className="line-clamp-1">{a.product.name}</span></th>)}
            </tr>
          </thead>
          <tbody className="divide-y divide-border">
            {RULES.map(([code, label]) => {
              const values = items.map((a) => pointsFor(a, code));
              if (values.every((v) => v === 0)) return null;
              return (
                <tr key={code}>
                  <th scope="row" className="px-4 py-2.5 text-left font-normal text-muted">{label}</th>
                  {values.map((v, i) => (
                    <td key={items[i].id} className={cn("px-4 py-2.5 text-right font-mono tabular", v < 0 ? "text-bad-ink" : v > 0 ? "text-good-ink" : "text-muted")}>
                      {v === 0 ? "—" : formatPoints(v)}
                    </td>
                  ))}
                </tr>
              );
            })}
            <tr className="font-semibold">
              <th scope="row" className="px-4 py-3 text-left">Final score</th>
              {items.map((a) => <td key={a.id} className="px-4 py-3 text-right font-mono tabular">{a.score}</td>)}
            </tr>
            <tr>
              <th scope="row" className="px-4 py-2.5 text-left font-normal text-muted">NOVA group</th>
              {items.map((a) => <td key={a.id} className="px-4 py-2.5 text-right tabular">{a.nova_group}</td>)}
            </tr>
          </tbody>
        </table>
      </div>

      {shared_concerns.length > 0 && (
        <p className="text-sm text-muted">
          <span className="font-semibold text-foreground">In all of them:</span> {shared_concerns.join(", ")}
        </p>
      )}
      <Button asChild variant="outline"><Link href="/compare?pick=1">Change products</Link></Button>
    </div>
  );
}

function CompareContent() {
  const params = useSearchParams();
  const ids = [...new Set(params.getAll("ids"))].slice(0, 4);
  const picking = params.get("pick") === "1" || ids.length < 2;
  return picking ? <Picker initial={ids} /> : <Comparison ids={ids} />;
}

export default function ComparePage() {
  return (
    <div>
      <PageHeader title="Compare products" description="See which product is the better pick, rule by rule." />
      <Suspense fallback={<PageSkeleton />}>
        <CompareContent />
      </Suspense>
    </div>
  );
}
