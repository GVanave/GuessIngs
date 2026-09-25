"use client";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { Sparkles } from "lucide-react";
import { api, ApiError } from "@/lib/api";
import { keys } from "@/lib/queries";
import { analyzeSchema, fieldErrors, type FieldErrors } from "@/lib/validation";
import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Field } from "@/components/ui/field";
import { Input, Textarea } from "@/components/ui/input";

export const EXAMPLES = [
  { name: "Chocolate Chip Granola Bar", text: "Whole grain oats, sugar, chocolate chips (sugar, cocoa butter, soy lecithin), brown rice syrup, canola oil, salt, natural flavor" },
  { name: "Orange Soda", text: "Carbonated water, high fructose corn syrup, citric acid, sodium benzoate (preservative), natural flavors, yellow 6, red 40" },
  { name: "Trail Mix", text: "Almonds, cashews, raisins, pumpkin seeds, sea salt" },
];

export interface AnalyzeFormValues {
  ingredients_text: string;
  product_name: string;
  brand?: string;
  sodium: string;
}

export function AnalyzeForm({
  initial,
  source = "manual",
  ocrText,
  showExamples = false,
  submitLabel = "Analyze ingredients",
  onCancel,
}: {
  initial?: Partial<AnalyzeFormValues>;
  source?: "manual" | "upload" | "camera";
  ocrText?: string;
  showExamples?: boolean;
  submitLabel?: string;
  onCancel?: () => void;
}) {
  const router = useRouter();
  const qc = useQueryClient();
  const [values, setValues] = useState<AnalyzeFormValues>({
    ingredients_text: initial?.ingredients_text ?? "",
    product_name: initial?.product_name ?? "",
    brand: initial?.brand ?? "",
    sodium: initial?.sodium ?? "",
  });
  const [errors, setErrors] = useState<FieldErrors>({});
  const [formError, setFormError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setFormError(null);
    const parsed = analyzeSchema.safeParse(values);
    if (!parsed.success) {
      setErrors(fieldErrors(parsed.error));
      return;
    }
    setErrors({});
    setLoading(true);
    try {
      const analysis = await api.analyze({
        ingredients_text: values.ingredients_text.trim(),
        product_name: values.product_name.trim() || null,
        brand: values.brand?.trim() || null,
        sodium_mg_per_100g: values.sodium.trim() ? Number(values.sodium) : null,
        source,
        ocr_text: ocrText ?? null,
      });
      qc.setQueryData(keys.analysis(analysis.id), analysis);
      qc.invalidateQueries({ queryKey: keys.dashboard });
      qc.invalidateQueries({ queryKey: ["history"] });
      router.push(`/analysis/${analysis.id}`);
    } catch (err) {
      setLoading(false);
      if (err instanceof ApiError) {
        if (err.status === 401) {
          router.replace("/login?next=/analyze");
          return;
        }
        if (["empty_input", "no_ingredients", "unparseable_input", "too_many_ingredients", "input_too_long"].includes(err.code)) {
          setErrors({ ingredients_text: err.message });
          return;
        }
        setFormError(err.message);
      } else {
        setFormError("Something went wrong. Please try again.");
      }
    }
  }

  const set = (k: keyof AnalyzeFormValues) => (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) =>
    setValues((v) => ({ ...v, [k]: e.target.value }));

  return (
    <form onSubmit={onSubmit} noValidate className="space-y-5" aria-label="Analyze ingredients">
      {formError && (
        <Alert tone="error" title="We couldn't analyze this product">
          {formError}
        </Alert>
      )}
      <Field id="product_name" label="Product name" optional error={errors.product_name}>
        {(p) => <Input {...p} placeholder="e.g. Crunchy Oat Granola" value={values.product_name} onChange={set("product_name")} maxLength={160} />}
      </Field>
      <Field
        id="ingredients_text"
        label="Ingredients"
        error={errors.ingredients_text}
        hint="Paste the list exactly as printed, separated by commas. Sub-ingredients in brackets are understood."
      >
        {(p) => (
          <Textarea
            {...p}
            rows={7}
            placeholder="Whole grain oats, sugar, sunflower oil, salt, natural flavor…"
            value={values.ingredients_text}
            onChange={set("ingredients_text")}
            maxLength={5000}
          />
        )}
      </Field>
      {showExamples && (
        <div>
          <p className="mb-2 text-xs font-medium text-muted">No label handy? Try an example:</p>
          <div className="flex flex-wrap gap-2">
            {EXAMPLES.map((ex) => (
              <button
                key={ex.name}
                type="button"
                onClick={() => setValues((v) => ({ ...v, ingredients_text: ex.text, product_name: ex.name }))}
                className="inline-flex h-9 items-center gap-1.5 rounded-full border border-border bg-surface px-3 text-xs font-medium hover:bg-surface-2"
              >
                <Sparkles className="size-3.5 text-muted" aria-hidden /> {ex.name}
              </button>
            ))}
          </div>
        </div>
      )}
      <Field
        id="sodium"
        label="Sodium per 100 g (mg)"
        optional
        error={errors.sodium}
        hint="From the nutrition table. Only used for the high-sodium rule (> 600 mg)."
      >
        {(p) => <Input {...p} inputMode="decimal" placeholder="e.g. 450" value={values.sodium} onChange={set("sodium")} className="max-w-48" />}
      </Field>
      <div className="flex flex-col-reverse gap-3 pt-1 sm:flex-row">
        {onCancel && (
          <Button type="button" variant="outline" size="lg" onClick={onCancel} disabled={loading}>
            Start over
          </Button>
        )}
        <Button type="submit" size="lg" loading={loading} className="sm:min-w-52">
          {loading ? "Analyzing…" : submitLabel}
        </Button>
      </div>
    </form>
  );
}
