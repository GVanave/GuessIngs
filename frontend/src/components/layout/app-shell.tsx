"use client";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { Bookmark, GitCompareArrows, History, Home, LogOut, PenLine, ScanLine, Settings, User } from "lucide-react";
import { api, ApiError } from "@/lib/api";
import { useMe } from "@/lib/queries";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Logo } from "./logo";
import { ThemeToggle } from "./theme-toggle";

const SIDEBAR = [
  { href: "/dashboard", label: "Home", icon: Home },
  { href: "/scan", label: "Scan product", icon: ScanLine },
  { href: "/analyze", label: "Manual analysis", icon: PenLine },
  { href: "/history", label: "History", icon: History },
  { href: "/saved", label: "Saved", icon: Bookmark },
  { href: "/compare", label: "Compare", icon: GitCompareArrows },
  { href: "/profile", label: "Profile", icon: User },
  { href: "/settings", label: "Settings", icon: Settings },
];

const BOTTOM = [
  { href: "/dashboard", label: "Home", icon: Home },
  { href: "/history", label: "History", icon: History },
  { href: "/scan", label: "Scan", icon: ScanLine, primary: true },
  { href: "/saved", label: "Saved", icon: Bookmark },
  { href: "/profile", label: "Profile", icon: User },
];

function isActive(pathname: string, href: string) {
  return pathname === href || pathname.startsWith(`${href}/`);
}

export function BottomNav({ pathname }: { pathname: string }) {
  return (
    <nav aria-label="Primary" className="fixed inset-x-0 bottom-0 z-40 border-t border-border bg-surface/95 backdrop-blur-md safe-bottom lg:hidden">
      <ul className="mx-auto grid max-w-md grid-cols-5 items-end px-2">
        {BOTTOM.map(({ href, label, icon: Icon, primary }) => {
          const active = isActive(pathname, href);
          return (
            <li key={href} className="flex justify-center">
              {primary ? (
                <Link
                  href={href}
                  aria-current={active ? "page" : undefined}
                  className="-mt-5 flex flex-col items-center gap-1 pb-2 text-[11px] font-semibold"
                >
                  <span className="grid size-14 place-items-center rounded-2xl bg-primary text-primary-foreground shadow-lg ring-4 ring-background transition-transform active:scale-95">
                    <Icon className="size-6" aria-hidden />
                  </span>
                  {label}
                </Link>
              ) : (
                <Link
                  href={href}
                  aria-current={active ? "page" : undefined}
                  className={cn(
                    "flex min-h-14 w-full flex-col items-center justify-center gap-1 rounded-xl text-[11px] font-medium transition-colors",
                    active ? "text-foreground" : "text-muted hover:text-foreground",
                  )}
                >
                  <Icon className={cn("size-5", active && "stroke-[2.4]")} aria-hidden />
                  {label}
                </Link>
              )}
            </li>
          );
        })}
      </ul>
    </nav>
  );
}

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const qc = useQueryClient();
  const me = useMe();

  useEffect(() => {
    if (me.error instanceof ApiError && me.error.status === 401) {
      router.replace(`/login?next=${encodeURIComponent(pathname)}`);
    }
  }, [me.error, pathname, router]);

  async function logout() {
    try {
      await api.logout();
    } finally {
      qc.clear();
      router.replace("/login");
    }
  }

  return (
    <div className="min-h-dvh">
      <a href="#main" className="sr-only focus:not-sr-only focus:fixed focus:left-4 focus:top-4 focus:z-50 focus:rounded-lg focus:bg-surface focus:px-4 focus:py-2 focus:shadow-card">
        Skip to content
      </a>
      {/* Desktop sidebar */}
      <aside className="fixed inset-y-0 left-0 z-30 hidden w-64 flex-col border-r border-border bg-surface px-4 py-5 lg:flex">
        <Logo href="/dashboard" className="px-2" />
        <Button asChild size="lg" className="mt-6 w-full">
          <Link href="/scan">
            <ScanLine /> Scan product
          </Link>
        </Button>
        <nav aria-label="Main" className="mt-6 flex-1">
          <ul className="space-y-1">
            {SIDEBAR.filter((i) => i.href !== "/scan").map(({ href, label, icon: Icon }) => {
              const active = isActive(pathname, href);
              return (
                <li key={href}>
                  <Link
                    href={href}
                    aria-current={active ? "page" : undefined}
                    className={cn(
                      "flex h-10 items-center gap-3 rounded-xl px-3 text-sm font-medium transition-colors",
                      active ? "bg-surface-2 text-foreground" : "text-muted hover:bg-surface-2 hover:text-foreground",
                    )}
                  >
                    <Icon className="size-4" aria-hidden />
                    {label}
                  </Link>
                </li>
              );
            })}
          </ul>
        </nav>
        <div className="flex items-center gap-2 border-t border-border pt-4">
          <div className="min-w-0 flex-1 px-2">
            <p className="truncate text-sm font-medium">{me.data?.full_name || "Your account"}</p>
            <p className="truncate text-xs text-muted">{me.data?.email}</p>
          </div>
          <ThemeToggle />
          <Button variant="ghost" size="icon" onClick={logout} aria-label="Sign out">
            <LogOut />
          </Button>
        </div>
      </aside>

      {/* Mobile top bar */}
      <header className="sticky top-0 z-30 flex h-14 items-center justify-between border-b border-border bg-background/90 px-4 backdrop-blur-md lg:hidden">
        <Logo href="/dashboard" />
        <div className="flex items-center">
          <Button asChild variant="ghost" size="icon" aria-label="Compare products">
            <Link href="/compare">
              <GitCompareArrows />
            </Link>
          </Button>
          <ThemeToggle />
        </div>
      </header>

      <main id="main" className="px-4 pb-32 pt-5 sm:px-6 lg:ml-64 lg:px-10 lg:pb-16 lg:pt-10">
        <div className="mx-auto w-full max-w-5xl">{children}</div>
      </main>
      <BottomNav pathname={pathname} />
    </div>
  );
}
