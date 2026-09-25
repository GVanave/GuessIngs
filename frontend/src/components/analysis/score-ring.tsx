"use client";
import { useEffect, useState } from "react";
import { cn } from "@/lib/utils";
import type { Verdict } from "@/lib/types";
import { VERDICT_META } from "./verdict";

export function ScoreRing({ score, verdict, size = 168, animate = true, className }: {
  score: number; verdict: Verdict; size?: number; animate?: boolean; className?: string;
}) {
  const [shown, setShown] = useState(animate ? 0 : score);
  useEffect(() => {
    if (!animate) return setShown(score);
    const id = requestAnimationFrame(() => setShown(score));
    return () => cancelAnimationFrame(id);
  }, [score, animate]);

  const stroke = size * 0.075;
  const r = (size - stroke) / 2;
  const c = 2 * Math.PI * r;
  const offset = c * (1 - shown / 100);
  const meta = VERDICT_META[verdict];

  return (
    <div
      className={cn("relative grid place-items-center", className)}
      style={{ width: size, height: size }}
      role="img"
      aria-label={`Score ${score} out of 100. Verdict ${verdict}: ${meta.description}.`}
    >
      <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`} className="-rotate-90" aria-hidden>
        <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke="var(--surface-2)" strokeWidth={stroke} />
        <circle
          cx={size / 2}
          cy={size / 2}
          r={r}
          fill="none"
          stroke={meta.stroke}
          strokeWidth={stroke}
          strokeLinecap="round"
          strokeDasharray={c}
          strokeDashoffset={offset}
          style={{ transition: "stroke-dashoffset 900ms cubic-bezier(0.2, 0.7, 0.2, 1)" }}
        />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center" aria-hidden>
        <span className="tabular font-bold tracking-tight" style={{ fontSize: size * 0.3, lineHeight: 1 }} data-testid="score-value">
          {score}
        </span>
        <span className="mt-1 text-xs font-medium text-muted">/ 100</span>
      </div>
    </div>
  );
}
