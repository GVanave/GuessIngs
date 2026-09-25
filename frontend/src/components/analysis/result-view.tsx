"use client";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import {
  ArrowRight, Bookmark, BookmarkCheck, CheckCircle2, ChevronDown, GitCompareArrows, Info, Lightbulb, PenLine,
  ShieldCheck, ThumbsUp, Trash2, TriangleAlert,
} from "lucide-react";
import { api, ApiError } from "@/lib/api";
import { keys, useMe, useToggleSave } from "@/lib/queries";
import type { Analysis, Highlight } from "@/lib/types";
import { cn, formatDate, PRODUCT_TYPE_LABELS } from "@/lib/utils";
import { Alert } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Dialog, DialogClose, DialogContent, DialogTrigger } from "@/components/ui/dialog";
import { CategoryChip } from "./category-chip";
import { ScoreBreakdown } from "./score-breakdown";
import { ScoreRing } from "./score-ring";
import { ScorePill, VerdictBadge } from "./verdict";

function HighlightList({ items, tone, empty }: { items: Highlight[]; tone: "good" | "bad"; empty: string }) {
  if (!items.length) return <p className="text-sm text-muted">{empty}</p>;
  return (
    <ul className="divide-y divide-border">
      {items.map((h) => (
        <li key={`${h.canonical_name}-${h.position}`} className="flex gap-3 py-3 first:pt-0 last:pb-0">
          <span
            className={cn(
              "mt-0.5 grid size-7 shrink-0 place-items-center rounded-lg text-xs font-bold tabular",
              tone === "good" ? "bg-good-soft text-good-ink" : "bg-bad-soft text-bad-ink",
            )}
            aria-label={`Ingredient number ${h.position}`}
          >
            {h.position}
          </span>
          <div className="min-w-0">
            <p className="font-medium capitalize">{h.name}</p>
            <p className="mt-0.5 text-sm text-muted">{h.reason}</p>
            <div className="mt-1.5 flex flex-wrap gap-1">
              {h.categories.map((c, i) => <CategoryChip key={c} category={c} label={h.labels[i]} />)}
            </div>
          </div>
        </li>
      ))}
    </ul>
  );
}

export function ResultView({ analysis }: { analysis: Analysis }) {
  const router = useRouter();
  const qc = useQueryClient();
  const toggleSave = useToggleSave();
  const me = useMe();
  const showNova = me.data?.preferences.show_nova ?? true;
  const [showAll, setShowAll] = useState(false);
  const a = analysis;
  const saved = a.product.is_saved;

  const verify = useMutation({
    mutationFn: () => api.verify(a.id),
    onSuccess: (v) =>
      v.matches
        ? toast.success(`Reproducible: recomputed score ${v.recomputed_score} matches (rules v${v.scoring_version}).`)
        : toast.warning(`Rules changed since this analysis: now ${v.recomputed_score} (rules v${v.scoring_version}).`),
    onError: (e) => toast.error(e instanceof ApiError ? e.message : "Verification failed."),
  });

  const remove = useMutation({
    mutationFn: () => api.deleteAnalysis(a.id),
    onSuccess: () => {
      qc.removeQueries({ queryKey: keys.analysis(a.id) });
      qc.invalidateQueries({ queryKey: ["history"] });
      qc.invalidateQueries({ queryKey: keys.dashboard });
      toast.success("Analysis deleted.");
      router.replace("/history");
    },
    onError: (e) => toast.error(e instanceof ApiError ? e.message : "Couldn't delete this analysis."),
  });

  function onSave() {
    toggleSave.mutate(
      { productId: a.product.id, saved: !saved },
      {
        onSuccess: () => toast.success(saved ? "Removed from saved products." : "Saved to your products."),
        onError: (e) => toast.error(e instanceof ApiError ? e.message : "Couldn't update saved products."),
      },
    );
  }

  const unique = a.ingredients.filter((i) => !i.is_duplicate);
  const visible = showAll ? a.ingredients : a.ingredients.slice(0, 12);

  return (
    <div className="space-y-5 lg:space-y-6">
      {/* Hero */}
      <Card className="overflow-hidden">
        <div className="flex flex-col items-center gap-6 p-6 sm:flex-row sm:items-center sm:p-8">
          <ScoreRing score={a.score} verdict={a.verdict} size={176} />
          <div className="min-w-0 flex-1 text-center sm:text-left">
            <p className="text-xs font-medium uppercase tracking-wider text-muted">
              {PRODUCT_TYPE_LABELS[a.product.category ?? "other"] ?? "Packaged food"}
              {a.product.brand && ` · ${a.product.brand}`}
            </p>
            <h1 className="mt-1 text-2xl font-bold tracking-tight sm:text-3xl" data-testid="product-name">{a.product.name}</h1>
            <div className="mt-3 flex flex-wrap items-center justify-center gap-2 sm:justify-start">
              <VerdictBadge verdict={a.verdict} size="lg" showDescription />
              {showNova && (
                <Badge tone="outline" title="NOVA food-processing group (1 = unprocessed, 4 = ultra-processed)">
                  NOVA {a.nova_group}
                </Badge>
              )}
            </div>
            <p className="mt-3 text-[15px] text-muted">{a.explanation.headline}</p>
          </div>
        </div>
        <div className="flex flex-wrap gap-2 border-t border-border bg-surface-2/50 px-4 py-3 sm:px-8">
          <Button variant={saved ? "default" : "outline"} size="sm" onClick={onSave} loading={toggleSave.isPending} aria-pressed={saved}>
            {saved ? <BookmarkCheck /> : <Bookmark />} {saved ? "Saved" : "Save product"}
          </Button>
          <Button asChild variant="outline" size="sm">
            <Link href={`/compare?ids=${a.id}`}><GitCompareArrows /> Compare</Link>
          </Button>
          <Button asChild variant="outline" size="sm">
            <Link href={`/analyze?from=${a.id}`}><PenLine /> Edit &amp; re-analyze</Link>
          </Button>
          <Dialog>
            <DialogTrigger asChild>
              <Button variant="ghost" size="sm" className="text-bad-ink sm:ml-auto"><Trash2 /> Delete</Button>
            </DialogTrigger>
            <DialogContent title="Delete this analysis?" description="This permanently removes it from your history.">
              <div className="flex justify-end gap-2">
                <DialogClose asChild><Button variant="outline">Cancel</Button></DialogClose>
                <Button variant="destructive" onClick={() => remove.mutate()} loading={remove.isPending}>Delete</Button>
              </div>
            </DialogContent>
          </Dialog>
        </div>
      </Card>

      {a.warnings.length > 0 && (
        <Alert tone="warn" title="Heads up">
          <ul className="space-y-1">{a.warnings.map((w) => <li key={w}>{w}</li>)}</ul>
        </Alert>
      )}

      {/* On mobile the two columns dissolve ("contents") so cards can be re-ordered: breakdown comes right after the explanation. */}
      <div className="flex flex-col gap-5 lg:grid lg:grid-cols-5 lg:gap-6">
        <div className="contents lg:col-span-3 lg:block lg:space-y-6">
          <Card className="order-1">
            <CardHeader>
              <CardTitle>Why this score?</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3 text-[15px] leading-relaxed">
              <p>{a.explanation.summary}</p>
              {a.explanation.ai_summary && (
                <p className="rounded-xl bg-surface-2 p-4 text-sm text-muted">
                  <span className="mb-1 block text-xs font-semibold uppercase tracking-wider">AI summary</span>
                  {a.explanation.ai_summary}
                </p>
              )}
            </CardContent>
          </Card>

          <div className="order-3 grid gap-5 sm:grid-cols-2 lg:gap-6">
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2"><ThumbsUp className="size-4 text-good" aria-hidden /> Positive ingredients</CardTitle>
              </CardHeader>
              <CardContent>
                <HighlightList items={a.positives} tone="good" empty="No standout whole-food ingredients found." />
              </CardContent>
            </Card>
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2"><TriangleAlert className="size-4 text-bad" aria-hidden /> Ingredients to watch</CardTitle>
              </CardHeader>
              <CardContent>
                <HighlightList items={a.concerns} tone="bad" empty="Nothing of concern found. Nice!" />
              </CardContent>
            </Card>
          </div>

          <Card className="order-4">
            <CardHeader>
              <CardTitle>Full ingredients</CardTitle>
              <CardDescription>{unique.length} ingredients, in label order. Numbers show each ingredient&apos;s position.</CardDescription>
            </CardHeader>
            <CardContent>
              <ol className="divide-y divide-border rounded-xl border border-border">
                {visible.map((ing, i) => (
                  <li key={`${ing.canonical_name}-${i}`} className={cn("flex items-start gap-3 px-3.5 py-2.5", ing.is_duplicate && "opacity-60")}>
                    <span className="w-6 shrink-0 pt-0.5 text-right font-mono text-xs text-muted tabular">{ing.position}</span>
                    <div className="min-w-0 flex-1">
                      <p className="text-sm font-medium">
                        {ing.display_name}
                        {ing.parent && <span className="font-normal text-muted"> · in {ing.parent}</span>}
                      </p>
                      {ing.display_name.toLowerCase() !== ing.canonical_name && (
                        <p className="text-xs text-muted">Recognized as {ing.canonical_name}</p>
                      )}
                      <div className="mt-1 flex flex-wrap gap-1">
                        {ing.categories.map((c, j) => <CategoryChip key={c} category={c} label={ing.labels[j]} />)}
                        {ing.is_duplicate && <Badge tone="outline">Duplicate — counted once</Badge>}
                        {ing.source === "ai" && <Badge tone="outline">AI-classified</Badge>}
                      </div>
                    </div>
                  </li>
                ))}
              </ol>
              {a.ingredients.length > 12 && (
                <Button variant="ghost" size="sm" className="mt-3" onClick={() => setShowAll((s) => !s)} aria-expanded={showAll}>
                  <ChevronDown className={cn("transition-transform", showAll && "rotate-180")} />
                  {showAll ? "Show fewer" : `Show all ${a.ingredients.length}`}
                </Button>
              )}
            </CardContent>
          </Card>
        </div>

        <div className="contents lg:col-span-2 lg:block lg:space-y-6">
          <Card className="order-2">
            <CardHeader>
              <CardTitle>Score breakdown</CardTitle>
              <CardDescription>The exact calculation, using fixed rules.</CardDescription>
            </CardHeader>
            <CardContent>
              <ScoreBreakdown lines={a.breakdown} score={a.score} />
              <Link href="/how-it-works" className="mt-3 inline-flex items-center gap-1 text-xs font-medium text-muted hover:text-foreground">
                <Info className="size-3.5" aria-hidden /> How the rules work
              </Link>
            </CardContent>
          </Card>

          <Card className="order-5">
            <CardHeader>
              <CardTitle className="flex items-center gap-2"><Lightbulb className="size-4 text-warn" aria-hidden /> Better alternatives</CardTitle>
            </CardHeader>
            <CardContent>
              {a.alternatives.length === 0 ? (
                <p className="text-sm text-muted">This is already a great choice.</p>
              ) : (
                <ul className="space-y-2.5">
                  {a.alternatives.map((alt, i) => (
                    <li key={`${alt.title}-${i}`}>
                      {alt.kind === "history" && alt.analysis_id ? (
                        <Link href={`/analysis/${alt.analysis_id}`} className="flex items-center gap-3 rounded-xl border border-border p-3 transition-colors hover:bg-surface-2">
                          {alt.score != null && alt.verdict && <ScorePill score={alt.score} verdict={alt.verdict} />}
                          <div className="min-w-0 flex-1">
                            <p className="truncate text-sm font-semibold">{alt.title}</p>
                            <p className="text-xs text-muted">{alt.description}</p>
                          </div>
                          <ArrowRight className="size-4 text-muted" aria-hidden />
                        </Link>
                      ) : (
                        <div className="rounded-xl bg-surface-2 p-3">
                          <p className="text-sm font-semibold">
                            {alt.kind === "tip" && <span className="mr-1.5 text-xs font-medium uppercase tracking-wider text-muted">Tip</span>}
                            {alt.title}
                          </p>
                          <p className="mt-0.5 text-xs text-muted">{alt.description}</p>
                        </div>
                      )}
                    </li>
                  ))}
                </ul>
              )}
            </CardContent>
          </Card>

          <Card className="order-6">
            <CardContent className="space-y-3 pt-5 text-xs text-muted sm:pt-6">
              <p className="flex items-center gap-1.5">
                <CheckCircle2 className="size-3.5" aria-hidden /> Analyzed {formatDate(a.created_at)} via {a.source === "manual" ? "manual entry" : a.source}
              </p>
              <p>
                Rules v{a.scoring_version} · Knowledge base {a.knowledge_base_version}
                {a.ai_model && ` · AI ${a.ai_model}`}
              </p>
              {a.sodium_mg_per_100g != null && <p>Sodium: {a.sodium_mg_per_100g} mg / 100 g</p>}
              <Button variant="outline" size="sm" onClick={() => verify.mutate()} loading={verify.isPending}>
                <ShieldCheck /> Verify score
              </Button>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
