import Link from "next/link";
import { ArrowRight, Check, ScanLine } from "lucide-react";
import { Button } from "@/components/ui/button";
import { DemoResultCard, FEATURES, STEPS } from "@/components/marketing";

export default function LandingPage() {
  return (
    <>
      <section className="relative overflow-hidden">
        <div aria-hidden className="pointer-events-none absolute -top-40 right-[-10%] size-[520px] rounded-full bg-accent/25 blur-3xl dark:bg-accent/10" />
        <div className="relative mx-auto grid max-w-6xl items-center gap-12 px-4 pb-16 pt-12 sm:px-6 md:pt-20 lg:grid-cols-[1.1fr_1fr] lg:pb-24">
          <div className="animate-fade-up">
            <p className="inline-flex items-center gap-2 rounded-full border border-border bg-surface px-3 py-1 text-xs font-medium text-muted">
              <span className="size-1.5 rounded-full bg-good" aria-hidden /> Transparent, rule-based food scores
            </p>
            <h1 className="mt-5 text-4xl font-bold leading-[1.05] tracking-tight sm:text-5xl lg:text-6xl">
              Know what&apos;s really inside your food.
            </h1>
            <p className="mt-5 max-w-xl text-lg leading-relaxed text-muted">
              Scan an ingredient label and get a clear 0–100 score, a GREEN / YELLOW / RED verdict, and the exact reasons
              behind it — in seconds.
            </p>
            <div className="mt-8 flex flex-col gap-3 sm:flex-row">
              <Button asChild size="xl">
                <Link href="/register">
                  <ScanLine /> Scan your first product
                </Link>
              </Button>
              <Button asChild size="xl" variant="outline">
                <Link href="/how-it-works">
                  How scoring works <ArrowRight />
                </Link>
              </Button>
            </div>
            <ul className="mt-8 grid gap-2 text-sm text-muted sm:grid-cols-2">
              {["Same ingredients → same score", "Every point explained", "Camera, upload or paste", "Free to use"].map((t) => (
                <li key={t} className="flex items-center gap-2">
                  <Check className="size-4 text-good" aria-hidden /> {t}
                </li>
              ))}
            </ul>
          </div>
          <div className="animate-fade-up [animation-delay:120ms]">
            <DemoResultCard />
          </div>
        </div>
      </section>

      <section aria-labelledby="features-title" className="border-t border-border bg-surface/50">
        <div className="mx-auto max-w-6xl px-4 py-16 sm:px-6 lg:py-24">
          <h2 id="features-title" className="text-3xl font-bold tracking-tight sm:text-4xl">Built for the grocery aisle</h2>
          <p className="mt-3 max-w-2xl text-muted">Everything you need to make a quick, informed choice — and nothing you don&apos;t.</p>
          <ul className="mt-10 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {FEATURES.slice(0, 6).map(({ icon: Icon, title, body }) => (
              <li key={title} className="rounded-2xl border border-border bg-surface p-6 shadow-card">
                <span className="grid size-10 place-items-center rounded-xl bg-accent/40 text-accent-foreground dark:bg-accent/15 dark:text-accent" aria-hidden>
                  <Icon className="size-5" />
                </span>
                <h3 className="mt-4 font-semibold">{title}</h3>
                <p className="mt-1.5 text-sm leading-relaxed text-muted">{body}</p>
              </li>
            ))}
          </ul>
          <Button asChild variant="link" className="mt-6">
            <Link href="/features">See all features <ArrowRight /></Link>
          </Button>
        </div>
      </section>

      <section aria-labelledby="how-title" className="border-t border-border">
        <div className="mx-auto max-w-6xl px-4 py-16 sm:px-6 lg:py-24">
          <h2 id="how-title" className="text-3xl font-bold tracking-tight sm:text-4xl">How it works</h2>
          <ol className="mt-10 grid gap-4 md:grid-cols-5">
            {STEPS.map((s) => (
              <li key={s.n} className="rounded-2xl border border-border bg-surface p-5">
                <span className="font-mono text-xs font-semibold text-muted">{s.n}</span>
                <h3 className="mt-2 font-semibold">{s.title}</h3>
                <p className="mt-1.5 text-sm leading-relaxed text-muted">{s.body}</p>
              </li>
            ))}
          </ol>
        </div>
      </section>

      <section className="border-t border-border">
        <div className="mx-auto max-w-6xl px-4 py-16 sm:px-6">
          <div className="flex flex-col items-start gap-6 rounded-3xl bg-primary p-8 text-primary-foreground sm:p-12 md:flex-row md:items-center md:justify-between">
            <div>
              <h2 className="text-2xl font-bold tracking-tight sm:text-3xl">Your next grocery run, decoded.</h2>
              <p className="mt-2 opacity-80">Create a free account and scan your first label in under a minute.</p>
            </div>
            <Button asChild size="xl" variant="accent">
              <Link href="/register">Get started free</Link>
            </Button>
          </div>
        </div>
      </section>
    </>
  );
}
