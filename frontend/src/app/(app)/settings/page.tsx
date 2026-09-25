"use client";
import { useEffect, useState } from "react";
import { useTheme } from "next-themes";
import { useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { Monitor, Moon, Sun } from "lucide-react";
import { api, ApiError } from "@/lib/api";
import { keys, useMe } from "@/lib/queries";
import type { Preferences } from "@/lib/types";
import { cn } from "@/lib/utils";
import { PageHeader } from "@/components/layout/page-header";
import { ScoringRulesTable } from "@/components/scoring-rules";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { PageSkeleton } from "@/components/ui/skeleton";
import { Switch } from "@/components/ui/switch";

const THEMES = [
  { value: "system", label: "System", icon: Monitor },
  { value: "light", label: "Light", icon: Sun },
  { value: "dark", label: "Dark", icon: Moon },
] as const;

export default function SettingsPage() {
  const me = useMe();
  const qc = useQueryClient();
  const { theme, setTheme } = useTheme();
  const [mounted, setMounted] = useState(false);
  useEffect(() => setMounted(true), []);
  if (!me.data) return <PageSkeleton />;
  const prefs = me.data.preferences;

  async function update(patch: Partial<Preferences>) {
    const next = { ...prefs, ...patch };
    qc.setQueryData(keys.me, { ...me.data!, preferences: next });
    try {
      const user = await api.updateMe({ preferences: next });
      qc.setQueryData(keys.me, user);
      toast.success("Settings saved.");
    } catch (err) {
      qc.setQueryData(keys.me, me.data);
      toast.error(err instanceof ApiError ? err.message : "Couldn't save settings.");
    }
  }

  return (
    <div className="max-w-2xl space-y-5">
      <PageHeader title="Settings" />
      <Card>
        <CardHeader>
          <CardTitle>Appearance</CardTitle>
          <CardDescription>Choose how GuessIngs looks on this device.</CardDescription>
        </CardHeader>
        <CardContent>
          <div role="radiogroup" aria-label="Theme" className="grid grid-cols-3 gap-2">
            {THEMES.map(({ value, label, icon: Icon }) => {
              const active = mounted && theme === value;
              return (
                <button
                  key={value}
                  type="button"
                  role="radio"
                  aria-checked={active}
                  onClick={() => { setTheme(value); void update({ theme: value }); }}
                  className={cn("flex flex-col items-center gap-2 rounded-xl border p-4 text-sm font-medium transition-colors",
                    active ? "border-ring bg-surface-2" : "border-border hover:bg-surface-2")}
                >
                  <Icon className="size-5" aria-hidden /> {label}
                </button>
              );
            })}
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader><CardTitle>Analysis</CardTitle></CardHeader>
        <CardContent className="divide-y divide-border">
          {([
            ["ai_explanations", "AI-written summaries", "Add a short AI-written explanation to results (the score itself never uses AI)."],
            ["show_nova", "Show NOVA processing group", "Display the food-processing classification on results."],
          ] as const).map(([key, label, desc]) => (
            <div key={key} className="flex items-center justify-between gap-4 py-4 first:pt-0 last:pb-0">
              <div>
                <label htmlFor={key} className="font-medium">{label}</label>
                <p id={`${key}-desc`} className="text-sm text-muted">{desc}</p>
              </div>
              <Switch id={key} checked={prefs[key]} onCheckedChange={(v) => update({ [key]: v })} aria-describedby={`${key}-desc`} />
            </div>
          ))}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Scoring rules</CardTitle>
          <CardDescription>The fixed rules used for every analysis.</CardDescription>
        </CardHeader>
        <CardContent><ScoringRulesTable /></CardContent>
      </Card>
    </div>
  );
}
