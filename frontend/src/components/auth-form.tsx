"use client";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { Eye, EyeOff } from "lucide-react";
import { api, ApiError } from "@/lib/api";
import { keys } from "@/lib/queries";
import { fieldErrors, loginSchema, registerSchema, type FieldErrors } from "@/lib/validation";
import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Field } from "@/components/ui/field";
import { Input } from "@/components/ui/input";

function safeNext(next: string | null): string {
  // Only allow internal redirects (prevents open-redirects).
  return next && next.startsWith("/") && !next.startsWith("//") ? next : "/dashboard";
}

export function AuthForm({ mode }: { mode: "login" | "register" }) {
  const router = useRouter();
  const params = useSearchParams();
  const qc = useQueryClient();
  const [values, setValues] = useState({ full_name: "", email: "", password: "" });
  const [errors, setErrors] = useState<FieldErrors>({});
  const [formError, setFormError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [show, setShow] = useState(false);
  const isRegister = mode === "register";

  const set = (k: keyof typeof values) => (e: React.ChangeEvent<HTMLInputElement>) =>
    setValues((v) => ({ ...v, [k]: e.target.value }));

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setFormError(null);
    const parsed = (isRegister ? registerSchema : loginSchema).safeParse(values);
    if (!parsed.success) {
      setErrors(fieldErrors(parsed.error));
      return;
    }
    setErrors({});
    setLoading(true);
    try {
      const res = isRegister
        ? await api.register({ email: values.email.trim(), password: values.password, full_name: values.full_name.trim() })
        : await api.login({ email: values.email.trim(), password: values.password });
      qc.setQueryData(keys.me, res.user);
      router.replace(safeNext(params.get("next")));
      router.refresh();
    } catch (err) {
      if (err instanceof ApiError && err.details && typeof err.details.fields === "object") {
        setErrors(err.details.fields as FieldErrors);
      }
      setFormError(err instanceof ApiError ? err.message : "Something went wrong. Please try again.");
      setLoading(false);
    }
  }

  return (
    <div>
      <h1 className="text-3xl font-bold tracking-tight">{isRegister ? "Create your account" : "Welcome back"}</h1>
      <p className="mt-2 text-sm text-muted">
        {isRegister ? "Start scanning labels in under a minute." : "Sign in to see your analyses and saved products."}
      </p>
      <form onSubmit={onSubmit} noValidate className="mt-8 space-y-4" aria-label={isRegister ? "Create account" : "Sign in"}>
        {formError && <Alert tone="error">{formError}</Alert>}
        {isRegister && (
          <Field id="full_name" label="Name" optional error={errors.full_name}>
            {(p) => <Input {...p} autoComplete="name" value={values.full_name} onChange={set("full_name")} />}
          </Field>
        )}
        <Field id="email" label="Email" error={errors.email}>
          {(p) => <Input {...p} type="email" autoComplete="email" inputMode="email" value={values.email} onChange={set("email")} required />}
        </Field>
        <Field
          id="password"
          label="Password"
          error={errors.password}
          hint={isRegister ? "At least 8 characters, with a letter and a number." : undefined}
        >
          {(p) => (
            <div className="relative">
              <Input
                {...p}
                type={show ? "text" : "password"}
                autoComplete={isRegister ? "new-password" : "current-password"}
                value={values.password}
                onChange={set("password")}
                className="pr-12"
                required
              />
              <button
                type="button"
                onClick={() => setShow((s) => !s)}
                className="absolute right-1 top-1 grid size-9 place-items-center rounded-lg text-muted hover:text-foreground"
                aria-label={show ? "Hide password" : "Show password"}
                aria-pressed={show}
              >
                {show ? <EyeOff className="size-4" /> : <Eye className="size-4" />}
              </button>
            </div>
          )}
        </Field>
        <Button type="submit" size="lg" className="w-full" loading={loading}>
          {isRegister ? "Create account" : "Sign in"}
        </Button>
      </form>
      <p className="mt-6 text-center text-sm text-muted">
        {isRegister ? "Already have an account? " : "New to GuessIngs? "}
        <Link href={isRegister ? "/login" : "/register"} className="font-semibold text-foreground underline-offset-4 hover:underline">
          {isRegister ? "Sign in" : "Create an account"}
        </Link>
      </p>
      {isRegister && (
        <p className="mt-4 text-center text-xs text-muted">
          By creating an account you agree to our <Link href="/terms" className="underline">Terms</Link> and{" "}
          <Link href="/privacy" className="underline">Privacy Policy</Link>.
        </p>
      )}
    </div>
  );
}
