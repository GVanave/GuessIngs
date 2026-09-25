export type Verdict = "GREEN" | "YELLOW" | "RED";

export interface Preferences {
  theme: "system" | "light" | "dark";
  show_nova: boolean;
  save_history: boolean;
  ai_explanations: boolean;
}

export interface User {
  id: string;
  email: string;
  full_name: string;
  preferences: Preferences;
  created_at: string;
}

export interface ProductBrief {
  id: string;
  name: string;
  brand: string | null;
  category: string | null;
  is_saved: boolean;
}

export interface ScoreLine {
  code: string;
  label: string;
  points: number;
  detail: string;
  ingredients: string[];
}

export interface Ingredient {
  display_name: string;
  canonical_name: string;
  position: number;
  parent: string | null;
  categories: string[];
  labels: string[];
  source: "kb" | "pattern" | "ai" | "unknown";
  is_duplicate: boolean;
}

export interface Highlight {
  name: string;
  canonical_name: string;
  position: number;
  categories: string[];
  labels: string[];
  reason: string;
}

export interface Alternative {
  kind: "swap" | "tip" | "history";
  title: string;
  description: string;
  analysis_id?: string | null;
  score?: number | null;
  verdict?: Verdict | null;
}

export interface AnalysisSummary {
  id: string;
  product: ProductBrief;
  score: number;
  verdict: Verdict;
  nova_group: number;
  source: "manual" | "upload" | "camera";
  ingredient_count: number;
  created_at: string;
}

export interface Analysis extends AnalysisSummary {
  raw_text: string;
  sodium_mg_per_100g: number | null;
  breakdown: ScoreLine[];
  explanation: { headline: string; summary: string; ai_summary: string | null; key_factors: string[] };
  ingredients: Ingredient[];
  concerns: Highlight[];
  positives: Highlight[];
  alternatives: Alternative[];
  warnings: string[];
  scoring_version: string;
  knowledge_base_version: string;
  ai_model: string | null;
  ai_used: boolean;
  input_hash: string;
}

export interface Page<T> {
  items: T[];
  total: number;
  limit: number;
  offset: number;
}

export interface Extraction {
  ingredients_text: string;
  product_name: string | null;
  brand: string | null;
  sodium_mg_per_100g: number | null;
  ocr_text: string;
  ocr_confidence: number;
  ai_used: boolean;
  quality_warnings: string[];
}

export interface SavedProduct {
  product: ProductBrief;
  latest: AnalysisSummary;
  notes: string | null;
  saved_at: string | null;
  analyses_count: number;
}

export interface Dashboard {
  total_analyses: number;
  saved_products: number;
  average_score: number | null;
  verdict_counts: Record<Verdict, number>;
  recent: AnalysisSummary[];
}

export interface Comparison {
  items: Analysis[];
  best_id: string | null;
  shared_concerns: string[];
}

export interface VerifyResult {
  analysis_id: string;
  stored_score: number;
  recomputed_score: number;
  matches: boolean;
  scoring_version: string;
}

export interface AnalyzeInput {
  ingredients_text: string;
  product_name?: string | null;
  brand?: string | null;
  sodium_mg_per_100g?: number | null;
  source?: "manual" | "upload" | "camera";
  ocr_text?: string | null;
}
