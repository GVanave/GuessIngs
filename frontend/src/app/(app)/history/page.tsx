"use client";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { useInfiniteQuery } from "@tanstack/react-query";
import { GitCompareArrows, History as HistoryIcon, Search, X } from "lucide-react";
import { api } from "@/lib/api";
import type { Verdict } from "@/lib/types";
import { cn } from "@/lib/utils";
import { AnalysisRow } from "@/components/analysis/analysis-row";
import { PageHeader } from "@/components/layout/page-header";
import { QueryError } from "@/components/query-error";
import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/empty-state";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";

const PAGE = 20;
const FILTERS: (Verdict | "ALL")[] = ["ALL", "GREEN", "YELLOW", "RED"];

export default function HistoryPage() {
  const router = useRouter();
  const [search, setSearch] = useState("");
  const [q, setQ] = useState("");
  const [verdict, setVerdict] = useState<Verdict | "ALL">("ALL");
  const [selecting, setSelecting] = useState(false);
  const [selected, setSelected] = useState<string[]>([]);

  useEffect(() => {
    const id = setTimeout(() => setQ(search.trim()), 300);
    return () => clearTimeout(id);
  }, [search]);

  const query = useInfiniteQuery({
    queryKey: ["history", { q, verdict }],
    queryFn: ({ pageParam }) => api.history({ limit: PAGE, offset: pageParam, q, verdict: verdict === "ALL" ? undefined : verdict }),
    initialPageParam: 0,
    getNextPageParam: (last) => (last.offset + last.items.length < last.total ? last.offset + last.items.length : undefined),
  });
  const items = query.data?.pages.flatMap((p) => p.items) ?? [];
  const total = query.data?.pages[0]?.total ?? 0;

  function toggle(id: string) {
    setSelected((s) => (s.includes(id) ? s.filter((x) => x !== id) : s.length >= 4 ? s : [...s, id]));
  }

  return (
    <div>
      <PageHeader
        title="History"
        description="Every analysis you've run, newest first."
        actions={
          <Button variant={selecting ? "default" : "outline"} size="sm" onClick={() => { setSelecting((s) => !s); setSelected([]); }} aria-pressed={selecting}>
            {selecting ? <X /> : <GitCompareArrows />} {selecting ? "Cancel" : "Select to compare"}
          </Button>
        }
      />
      <div className="mb-4 flex flex-col gap-3 sm:flex-row sm:items-center">
        <div className="relative flex-1">
          <Search className="pointer-events-none absolute left-3.5 top-1/2 size-4 -translate-y-1/2 text-muted" aria-hidden />
          <Input type="search" placeholder="Search products or brands" value={search} onChange={(e) => setSearch(e.target.value)} className="pl-10" aria-label="Search history" />
        </div>
        <div role="group" aria-label="Filter by verdict" className="flex gap-1.5 overflow-x-auto">
          {FILTERS.map((f) => (
            <button
              key={f}
              type="button"
              onClick={() => setVerdict(f)}
              aria-pressed={verdict === f}
              className={cn(
                "h-9 shrink-0 rounded-full border px-3.5 text-xs font-semibold transition-colors",
                verdict === f ? "border-primary bg-primary text-primary-foreground" : "border-border bg-surface text-muted hover:text-foreground",
              )}
            >
              {f === "ALL" ? "All" : f}
            </button>
          ))}
        </div>
      </div>

      {query.isError ? (
        <QueryError error={query.error} onRetry={() => query.refetch()} />
      ) : query.isPending ? (
        <div className="space-y-2">{[0, 1, 2, 3].map((i) => <Skeleton key={i} className="h-16" />)}</div>
      ) : items.length === 0 ? (
        <EmptyState
          icon={<HistoryIcon />}
          title={q || verdict !== "ALL" ? "No matches" : "No analyses yet"}
          description={q || verdict !== "ALL" ? "Try a different search or filter." : "Your analyses will appear here after you scan or type a product."}
          action={!q && verdict === "ALL" ? <Button asChild><Link href="/scan">Scan a product</Link></Button> : undefined}
        />
      ) : (
        <>
          <p className="mb-2 text-xs text-muted" aria-live="polite">{total} {total === 1 ? "analysis" : "analyses"}</p>
          <ul className="space-y-2">
            {items.map((a) => (
              <li key={a.id}>
                <AnalysisRow a={a} selectable={selecting} selected={selected.includes(a.id)} onToggle={() => toggle(a.id)} />
              </li>
            ))}
          </ul>
          {query.hasNextPage && (
            <div className="mt-4 flex justify-center">
              <Button variant="outline" onClick={() => query.fetchNextPage()} loading={query.isFetchingNextPage}>Load more</Button>
            </div>
          )}
        </>
      )}

      {selecting && (
        <div className="fixed inset-x-4 bottom-24 z-40 mx-auto flex max-w-md items-center justify-between gap-3 rounded-2xl border border-border bg-surface p-3 pl-5 shadow-card lg:bottom-8 lg:ml-[calc(50%+8rem)] lg:-translate-x-1/2">
          <p className="text-sm font-medium" aria-live="polite">{selected.length} of 4 selected</p>
          <Button disabled={selected.length < 2} onClick={() => router.push(`/compare?${selected.map((id) => `ids=${id}`).join("&")}`)}>
            Compare
          </Button>
        </div>
      )}
    </div>
  );
}
