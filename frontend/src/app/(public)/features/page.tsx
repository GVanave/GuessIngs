import type { Metadata } from "next";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { FEATURES } from "@/components/marketing";

export const metadata: Metadata = { title: "Features" };

export default function FeaturesPage() {
  return (
    <div className="mx-auto max-w-6xl px-4 py-14 sm:px-6 lg:py-20">
      <h1 className="text-4xl font-bold tracking-tight sm:text-5xl">Features</h1>
      <p className="mt-4 max-w-2xl text-lg text-muted">
        AI does the reading. Transparent rules do the scoring. You get a clear answer you can trust.
      </p>
      <ul className="mt-12 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {FEATURES.map(({ icon: Icon, title, body }) => (
          <li key={title} className="rounded-2xl border border-border bg-surface p-6 shadow-card">
            <Icon className="size-6 text-good" aria-hidden />
            <h2 className="mt-4 font-semibold">{title}</h2>
            <p className="mt-1.5 text-sm leading-relaxed text-muted">{body}</p>
          </li>
        ))}
      </ul>
      <Button asChild size="lg" className="mt-12">
        <Link href="/register">Start scanning</Link>
      </Button>
    </div>
  );
}
