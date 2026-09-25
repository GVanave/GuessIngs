import { Logo } from "@/components/layout/logo";
import { ThemeToggle } from "@/components/layout/theme-toggle";

export default function AuthLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="grid min-h-dvh lg:grid-cols-2">
      <div className="flex flex-col px-4 py-6 sm:px-8">
        <div className="flex items-center justify-between">
          <Logo />
          <ThemeToggle />
        </div>
        <main id="main" className="flex flex-1 items-center justify-center py-10">
          <div className="w-full max-w-sm animate-fade-up">{children}</div>
        </main>
      </div>
      <div className="relative hidden overflow-hidden bg-primary p-12 text-primary-foreground lg:flex lg:flex-col lg:justify-end">
        <div aria-hidden className="absolute -right-24 -top-24 size-96 rounded-full bg-accent/30 blur-3xl" />
        <blockquote className="relative max-w-md">
          <p className="text-3xl font-semibold leading-tight tracking-tight">
            &ldquo;Same ingredients, same score — with every point explained.&rdquo;
          </p>
          <footer className="mt-4 text-sm opacity-70">The GuessIngs scoring promise</footer>
        </blockquote>
      </div>
    </div>
  );
}
