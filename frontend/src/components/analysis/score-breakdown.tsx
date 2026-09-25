import { cn, formatPoints } from "@/lib/utils";
import type { ScoreLine } from "@/lib/types";

/** Receipt-style score calculation: every line that contributed to the final score. */
export function ScoreBreakdown({ lines, score }: { lines: ScoreLine[]; score: number }) {
  const total = lines.reduce((s, l) => s + l.points, 0);
  return (
    <div className="rounded-xl border border-border bg-surface-2/60 font-mono text-[13px] sm:text-sm">
      <table className="w-full border-collapse">
        <caption className="sr-only">Score calculation</caption>
        <thead className="sr-only">
          <tr>
            <th scope="col">Rule</th>
            <th scope="col">Points</th>
          </tr>
        </thead>
        <tbody>
          {lines.map((line, i) => (
            <tr key={`${line.code}-${i}`} className="align-top" data-testid={`line-${line.code}`}>
              <th scope="row" className="px-4 py-2.5 text-left font-normal">
                <span className="block font-sans text-sm font-medium text-foreground">{line.label}</span>
                {line.code !== "start" && <span className="mt-0.5 block font-sans text-xs text-muted">{line.detail}</span>}
              </th>
              <td
                className={cn(
                  "whitespace-nowrap px-4 py-2.5 text-right tabular font-semibold",
                  line.code === "start" ? "text-foreground" : line.points < 0 ? "text-bad-ink" : line.points > 0 ? "text-good-ink" : "text-muted",
                )}
              >
                {line.code === "start" ? line.points : formatPoints(line.points)}
              </td>
            </tr>
          ))}
        </tbody>
        <tfoot>
          <tr className="border-t border-dashed border-muted/40">
            <th scope="row" className="px-4 py-3 text-left font-sans text-sm font-semibold">
              Final score
            </th>
            <td className="px-4 py-3 text-right text-base font-bold tabular" data-testid="final-score">
              {score}
            </td>
          </tr>
        </tfoot>
      </table>
      {total !== score && <p className="sr-only">Lines total {total}, clamped to {score}.</p>}
    </div>
  );
}
