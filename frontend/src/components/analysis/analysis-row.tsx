import Link from "next/link";
import { Camera, ChevronRight, ImageUp, Keyboard } from "lucide-react";
import type { AnalysisSummary } from "@/lib/types";
import { cn, formatRelative } from "@/lib/utils";
import { ScorePill, VerdictBadge } from "./verdict";

const SOURCE_ICON = { camera: Camera, upload: ImageUp, manual: Keyboard };

export function AnalysisRow({ a, selectable, selected, onToggle }: {
  a: AnalysisSummary; selectable?: boolean; selected?: boolean; onToggle?: () => void;
}) {
  const SourceIcon = SOURCE_ICON[a.source];
  const body = (
    <>
      <ScorePill score={a.score} verdict={a.verdict} />
      <div className="min-w-0 flex-1">
        <p className="truncate font-semibold">{a.product.name}</p>
        <p className="mt-0.5 flex items-center gap-1.5 truncate text-xs text-muted">
          <SourceIcon className="size-3.5 shrink-0" aria-hidden />
          <span className="sr-only">Source: {a.source}.</span>
          {a.product.brand ? `${a.product.brand} · ` : ""}
          {a.ingredient_count} ingredients · {formatRelative(a.created_at)}
        </p>
      </div>
      <VerdictBadge verdict={a.verdict} size="sm" className="hidden sm:inline-flex" />
    </>
  );
  if (selectable) {
    return (
      <label className={cn("flex min-h-16 cursor-pointer items-center gap-3 rounded-2xl border bg-surface p-3 transition-colors", selected ? "border-ring bg-surface-2" : "border-border hover:bg-surface-2")}>
        <input type="checkbox" checked={selected} onChange={onToggle} className="size-5 accent-[var(--primary)]" aria-label={`Select ${a.product.name}`} />
        {body}
      </label>
    );
  }
  return (
    <Link href={`/analysis/${a.id}`} className="flex min-h-16 items-center gap-3 rounded-2xl border border-border bg-surface p-3 transition-colors hover:bg-surface-2">
      {body}
      <ChevronRight className="size-4 shrink-0 text-muted" aria-hidden />
    </Link>
  );
}
