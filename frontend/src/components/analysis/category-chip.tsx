import { cn } from "@/lib/utils";

const NEGATIVE = new Set(["added_sugar", "artificial_sweetener", "hydrogenated_oil", "artificial_color", "artificial_flavor", "preservative", "emulsifier"]);
const POSITIVE = new Set(["fiber_protein", "healthy_fat", "whole_food"]);

export function categoryTone(category: string): "bad" | "good" | "neutral" {
  if (NEGATIVE.has(category)) return "bad";
  if (POSITIVE.has(category)) return "good";
  return "neutral";
}

export function CategoryChip({ category, label }: { category: string; label: string }) {
  const tone = categoryTone(category);
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 rounded-md px-1.5 py-0.5 text-[11px] font-medium",
        tone === "bad" && "bg-bad-soft text-bad-ink",
        tone === "good" && "bg-good-soft text-good-ink",
        tone === "neutral" && "bg-surface-2 text-muted",
      )}
    >
      <span aria-hidden>{tone === "bad" ? "−" : tone === "good" ? "+" : "·"}</span>
      {label}
    </span>
  );
}
