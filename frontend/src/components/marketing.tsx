import { Bookmark, Camera, FileText, GitCompareArrows, History, Scale, ShieldCheck, Sparkles, Zap } from "lucide-react";
import { ScoreBreakdown } from "@/components/analysis/score-breakdown";
import { ScoreRing } from "@/components/analysis/score-ring";
import { VerdictBadge } from "@/components/analysis/verdict";

export const FEATURES = [
  { icon: Camera, title: "Scan any label", body: "Point your camera at the ingredients panel or upload a photo. OCR and AI read it in seconds." },
  { icon: Scale, title: "Deterministic scoring", body: "A transparent rule engine — not an AI guess — scores every product. Same list, same score. Always." },
  { icon: FileText, title: "Every point explained", body: "See the exact calculation: which ingredient cost how many points, and why." },
  { icon: Sparkles, title: "Smart ingredient matching", body: "Synonyms, E-numbers and sub-ingredients are normalized, so 'sucrose' and 'E211' are understood." },
  { icon: GitCompareArrows, title: "Compare side by side", body: "Put up to four products next to each other and see which is the better pick." },
  { icon: History, title: "History & saved products", body: "Every analysis is stored and reproducible. Save your favorites for quick reference." },
  { icon: Zap, title: "Better alternatives", body: "Get practical swaps and see higher-scoring products you've already scanned." },
  { icon: Bookmark, title: "Works everywhere", body: "Designed mobile-first for the grocery aisle, and just as good on tablet and desktop." },
  { icon: ShieldCheck, title: "Private & secure", body: "Encrypted sessions, hashed passwords and no selling of your data. Delete it any time." },
];

export const STEPS = [
  { n: "01", title: "Scan, upload or paste", body: "Capture the ingredient list with your camera, upload a photo, or type it in." },
  { n: "02", title: "Read & normalize", body: "OCR and AI extract the list; each ingredient is normalized and matched against our knowledge base." },
  { n: "03", title: "Classify", body: "Ingredients are classified — added sugar, preservative, whole-food fiber and more." },
  { n: "04", title: "Score with fixed rules", body: "A deterministic engine applies published rules to reach a 0–100 score and a verdict." },
  { n: "05", title: "Understand & decide", body: "See why, what to watch, what's good, and better alternatives. Saved to your history." },
];

export function DemoResultCard() {
  const lines = [
    { code: "start", label: "Starting score", points: 100, detail: "", ingredients: [] },
    { code: "added_sugar", label: "Added sugar", points: -25, detail: "sugar is the 2nd ingredient (−25)", ingredients: ["sugar"] },
    { code: "preservative", label: "Preservative", points: -6, detail: "−6 for each: potassium sorbate", ingredients: [] },
    { code: "fiber_protein", label: "Whole-food fiber/protein source", points: 5, detail: "+5 each within the first 5", ingredients: [] },
  ];
  return (
    <div className="rounded-3xl border border-border bg-surface p-5 shadow-card sm:p-6" aria-label="Example analysis result">
      <div className="flex items-center gap-5">
        <ScoreRing score={74} verdict="YELLOW" size={112} />
        <div className="min-w-0">
          <p className="text-xs font-medium uppercase tracking-wider text-muted">Example</p>
          <p className="mt-0.5 truncate text-lg font-semibold">Oat &amp; Honey Granola</p>
          <VerdictBadge verdict="YELLOW" showDescription className="mt-2" />
        </div>
      </div>
      <div className="mt-5">
        <ScoreBreakdown lines={lines} score={74} />
      </div>
    </div>
  );
}
