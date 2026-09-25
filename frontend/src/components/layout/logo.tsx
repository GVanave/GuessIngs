import Link from "next/link";
import { cn } from "@/lib/utils";

export function LogoMark({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 32 32" className={cn("size-8", className)} aria-hidden>
      <rect width="32" height="32" rx="9" fill="var(--primary)" />
      <circle cx="16" cy="16" r="9" fill="none" stroke="var(--accent)" strokeWidth="2.5" strokeDasharray="42 60" strokeLinecap="round" transform="rotate(-90 16 16)" />
      <path d="M13 17.5c0-3 2.2-5.3 5.5-5.5.2 3.3-2 5.7-5.5 5.5Zm0 0-1.8 2.2" fill="none" stroke="var(--primary-foreground)" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

export function Logo({ href = "/", className }: { href?: string; className?: string }) {
  return (
    <Link href={href} className={cn("inline-flex items-center gap-2.5 rounded-lg", className)} aria-label="GuessIngs home">
      <LogoMark />
      <span className="text-[17px] font-bold tracking-tight">
        Guess<span className="text-muted">Ings</span>
      </span>
    </Link>
  );
}
