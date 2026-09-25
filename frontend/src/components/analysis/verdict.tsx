import { CheckCircle2, AlertTriangle, OctagonAlert } from "lucide-react";
import { cn } from "@/lib/utils";
import type { Verdict } from "@/lib/types";

export const VERDICT_META: Record<Verdict, { label: string; description: string; Icon: typeof CheckCircle2; text: string; soft: string; stroke: string }> = {
  GREEN: { label: "Green", description: "Good choice", Icon: CheckCircle2, text: "text-good-ink", soft: "bg-good-soft", stroke: "var(--good)" },
  YELLOW: { label: "Yellow", description: "Okay occasionally", Icon: AlertTriangle, text: "text-warn-ink", soft: "bg-warn-soft", stroke: "var(--warn)" },
  RED: { label: "Red", description: "Best limited", Icon: OctagonAlert, text: "text-bad-ink", soft: "bg-bad-soft", stroke: "var(--bad)" },
};

/** Verdict badge: always shows an icon and a text label, never color alone. */
export function VerdictBadge({ verdict, size = "md", showDescription = false, className }: {
  verdict: Verdict; size?: "sm" | "md" | "lg"; showDescription?: boolean; className?: string;
}) {
  const meta = VERDICT_META[verdict];
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full font-semibold uppercase tracking-wide",
        meta.soft, meta.text,
        size === "sm" && "px-2 py-0.5 text-[11px] [&_svg]:size-3.5",
        size === "md" && "px-3 py-1 text-xs [&_svg]:size-4",
        size === "lg" && "px-4 py-1.5 text-sm [&_svg]:size-5",
        className,
      )}
      data-verdict={verdict}
    >
      <meta.Icon aria-hidden />
      <span>{verdict}</span>
      {showDescription && <span className="font-medium normal-case tracking-normal">· {meta.description}</span>}
    </span>
  );
}

export function ScorePill({ score, verdict, className }: { score: number; verdict: Verdict; className?: string }) {
  const meta = VERDICT_META[verdict];
  return (
    <span
      className={cn("inline-flex h-11 min-w-11 flex-col items-center justify-center rounded-xl px-2 tabular", meta.soft, meta.text, className)}
      aria-label={`Score ${score} out of 100, ${verdict}`}
    >
      <span className="text-base font-bold leading-none">{score}</span>
      <meta.Icon className="mt-0.5 size-3" aria-hidden />
    </span>
  );
}
