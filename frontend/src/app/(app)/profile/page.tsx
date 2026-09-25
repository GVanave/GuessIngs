"use client";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { LogOut, Settings } from "lucide-react";
import { api, ApiError } from "@/lib/api";
import { keys, useMe } from "@/lib/queries";
import { passwordSchema } from "@/lib/validation";
import { PageHeader } from "@/components/layout/page-header";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Dialog, DialogClose, DialogContent, DialogTrigger } from "@/components/ui/dialog";
import { Field } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { PageSkeleton } from "@/components/ui/skeleton";

export default function ProfilePage() {
  const router = useRouter();
  const qc = useQueryClient();
  const me = useMe();
  const stats = useQuery({ queryKey: keys.dashboard, queryFn: api.dashboard });
  const [name, setName] = useState("");
  const [savingName, setSavingName] = useState(false);
  const [pw, setPw] = useState({ current: "", next: "" });
  const [pwError, setPwError] = useState<string | undefined>();
  const [pwLoading, setPwLoading] = useState(false);
  const [delPw, setDelPw] = useState("");
  const [delError, setDelError] = useState<string | undefined>();
  const [deleting, setDeleting] = useState(false);

  useEffect(() => { if (me.data) setName(me.data.full_name); }, [me.data]);
  if (!me.data) return <PageSkeleton />;

  async function saveName(e: React.FormEvent) {
    e.preventDefault();
    setSavingName(true);
    try {
      const user = await api.updateMe({ full_name: name });
      qc.setQueryData(keys.me, user);
      toast.success("Profile updated.");
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "Couldn't update your profile.");
    } finally {
      setSavingName(false);
    }
  }

  async function changePassword(e: React.FormEvent) {
    e.preventDefault();
    const check = passwordSchema.safeParse(pw.next);
    if (!check.success) return setPwError(check.error.issues[0].message);
    setPwError(undefined);
    setPwLoading(true);
    try {
      await api.changePassword({ current_password: pw.current, new_password: pw.next });
      setPw({ current: "", next: "" });
      toast.success("Password changed. Other devices were signed out.");
    } catch (err) {
      setPwError(err instanceof ApiError ? err.message : "Couldn't change your password.");
    } finally {
      setPwLoading(false);
    }
  }

  async function deleteAccount() {
    setDeleting(true);
    try {
      await api.deleteAccount(delPw);
      qc.clear();
      router.replace("/");
    } catch (err) {
      setDelError(err instanceof ApiError ? err.message : "Couldn't delete your account.");
      setDeleting(false);
    }
  }

  async function logout() {
    await api.logout().catch(() => undefined);
    qc.clear();
    router.replace("/login");
  }

  const initials = (me.data.full_name || me.data.email).split(/\s+/).map((s) => s[0]).join("").slice(0, 2).toUpperCase();

  return (
    <div className="max-w-2xl space-y-5">
      <PageHeader title="Profile" />
      <Card>
        <CardContent className="flex items-center gap-4 pt-5 sm:pt-6">
          <span className="grid size-14 place-items-center rounded-2xl bg-accent text-lg font-bold text-accent-foreground" aria-hidden>{initials}</span>
          <div className="min-w-0 flex-1">
            <p className="truncate text-lg font-semibold">{me.data.full_name || "Your account"}</p>
            <p className="truncate text-sm text-muted">{me.data.email}</p>
          </div>
        </CardContent>
        {stats.data && (
          <dl className="grid grid-cols-3 border-t border-border text-center">
            <div className="p-4"><dt className="text-xs text-muted">Analyzed</dt><dd className="text-xl font-bold tabular">{stats.data.total_analyses}</dd></div>
            <div className="border-x border-border p-4"><dt className="text-xs text-muted">Saved</dt><dd className="text-xl font-bold tabular">{stats.data.saved_products}</dd></div>
            <div className="p-4"><dt className="text-xs text-muted">Avg score</dt><dd className="text-xl font-bold tabular">{stats.data.average_score ?? "—"}</dd></div>
          </dl>
        )}
      </Card>

      <Card>
        <CardHeader><CardTitle>Personal details</CardTitle></CardHeader>
        <CardContent>
          <form onSubmit={saveName} className="flex flex-col gap-3 sm:flex-row sm:items-end">
            <div className="flex-1">
              <Field id="name" label="Name">{(p) => <Input {...p} value={name} onChange={(e) => setName(e.target.value)} maxLength={120} autoComplete="name" />}</Field>
            </div>
            <Button type="submit" loading={savingName}>Save</Button>
          </form>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Change password</CardTitle>
          <CardDescription>You&apos;ll stay signed in here; other devices will be signed out.</CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={changePassword} className="space-y-4" noValidate>
            <Field id="current_password" label="Current password">
              {(p) => <Input {...p} type="password" autoComplete="current-password" value={pw.current} onChange={(e) => setPw({ ...pw, current: e.target.value })} />}
            </Field>
            <Field id="new_password" label="New password" error={pwError} hint="At least 8 characters, with a letter and a number.">
              {(p) => <Input {...p} type="password" autoComplete="new-password" value={pw.next} onChange={(e) => setPw({ ...pw, next: e.target.value })} />}
            </Field>
            <Button type="submit" loading={pwLoading} disabled={!pw.current || !pw.next}>Update password</Button>
          </form>
        </CardContent>
      </Card>

      <div className="flex flex-wrap gap-2">
        <Button asChild variant="outline"><Link href="/settings"><Settings /> Settings</Link></Button>
        <Button variant="outline" onClick={logout}><LogOut /> Sign out</Button>
      </div>

      <Card className="border-bad/30">
        <CardHeader>
          <CardTitle>Delete account</CardTitle>
          <CardDescription>Permanently delete your account, history and saved products. This can&apos;t be undone.</CardDescription>
        </CardHeader>
        <CardContent>
          <Dialog>
            <DialogTrigger asChild><Button variant="destructive">Delete account</Button></DialogTrigger>
            <DialogContent title="Delete your account?" description="Enter your password to confirm. All your data will be permanently removed.">
              <div className="space-y-4">
                <Field id="delete_password" label="Password" error={delError}>
                  {(p) => <Input {...p} type="password" autoComplete="current-password" value={delPw} onChange={(e) => setDelPw(e.target.value)} />}
                </Field>
                <div className="flex justify-end gap-2">
                  <DialogClose asChild><Button variant="outline">Cancel</Button></DialogClose>
                  <Button variant="destructive" onClick={deleteAccount} loading={deleting} disabled={!delPw}>Delete forever</Button>
                </div>
              </div>
            </DialogContent>
          </Dialog>
        </CardContent>
      </Card>
    </div>
  );
}
