import type { Metadata } from "next";
import { ScoringRulesTable } from "@/components/scoring-rules";
import { STEPS } from "@/components/marketing";

export const metadata: Metadata = { title: "How it works" };

export default function HowItWorksPage() {
  return (
    <div className="mx-auto max-w-4xl px-4 py-14 sm:px-6 lg:py-20">
      <h1 className="text-4xl font-bold tracking-tight sm:text-5xl">How it works</h1>
      <p className="mt-4 text-lg text-muted">
        AI reads and understands the label. A fixed, published rule set calculates the score. The AI never decides your
        score — so the same ingredient list always gets the same result.
      </p>
      <ol className="mt-10 space-y-3">
        {STEPS.map((s) => (
          <li key={s.n} className="flex gap-4 rounded-2xl border border-border bg-surface p-5">
            <span className="font-mono text-sm font-semibold text-muted">{s.n}</span>
            <div>
              <h2 className="font-semibold">{s.title}</h2>
              <p className="mt-1 text-sm text-muted">{s.body}</p>
            </div>
          </li>
        ))}
      </ol>
      <h2 className="mt-16 text-2xl font-bold tracking-tight">The scoring rules</h2>
      <p className="mt-2 text-muted">Every product starts at 100. These rules are applied, and the result is kept between 0 and 100.</p>
      <ScoringRulesTable />
    </div>
  );
}
