"use client";
import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { toast } from "sonner";
import { Bookmark, BookmarkX } from "lucide-react";
import { api, ApiError } from "@/lib/api";
import { keys, useToggleSave } from "@/lib/queries";
import { formatRelative, PRODUCT_TYPE_LABELS } from "@/lib/utils";
import { ScorePill, VerdictBadge } from "@/components/analysis/verdict";
import { PageHeader } from "@/components/layout/page-header";
import { QueryError } from "@/components/query-error";
import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/empty-state";
import { Skeleton } from "@/components/ui/skeleton";

export default function SavedPage() {
  const q = useQuery({ queryKey: keys.saved, queryFn: api.saved });
  const toggle = useToggleSave();

  return (
    <div>
      <PageHeader title="Saved products" description="Products you want to remember — the good, the bad and the in-between." />
      {q.isError ? (
        <QueryError error={q.error} onRetry={() => q.refetch()} />
      ) : q.isPending ? (
        <div className="grid gap-3 sm:grid-cols-2">{[0, 1, 2, 3].map((i) => <Skeleton key={i} className="h-36" />)}</div>
      ) : q.data.length === 0 ? (
        <EmptyState
          icon={<Bookmark />}
          title="Nothing saved yet"
          description="Tap “Save product” on any result to keep it here for quick reference."
          action={<Button asChild><Link href="/history">Browse history</Link></Button>}
        />
      ) : (
        <ul className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
          {q.data.map((s) => (
            <li key={s.product.id} className="flex flex-col rounded-2xl border border-border bg-surface p-4 shadow-card">
              <Link href={`/analysis/${s.latest.id}`} className="flex items-start gap-3 rounded-xl">
                <ScorePill score={s.latest.score} verdict={s.latest.verdict} />
                <div className="min-w-0 flex-1">
                  <p className="truncate font-semibold">{s.product.name}</p>
                  <p className="truncate text-xs text-muted">
                    {PRODUCT_TYPE_LABELS[s.product.category ?? "other"]}{s.product.brand ? ` · ${s.product.brand}` : ""}
                  </p>
                </div>
              </Link>
              {s.notes && <p className="mt-3 line-clamp-2 text-sm text-muted">{s.notes}</p>}
              <div className="mt-auto flex items-center justify-between pt-4">
                <div className="flex items-center gap-2">
                  <VerdictBadge verdict={s.latest.verdict} size="sm" />
                  <span className="text-xs text-muted">{s.saved_at ? `Saved ${formatRelative(s.saved_at)}` : ""}</span>
                </div>
                <Button
                  variant="ghost"
                  size="sm"
                  aria-label={`Remove ${s.product.name} from saved`}
                  onClick={() =>
                    toggle.mutate(
                      { productId: s.product.id, saved: false },
                      {
                        onSuccess: () => toast.success("Removed from saved products."),
                        onError: (e) => toast.error(e instanceof ApiError ? e.message : "Couldn't update."),
                      },
                    )
                  }
                >
                  <BookmarkX /> Remove
                </Button>
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
