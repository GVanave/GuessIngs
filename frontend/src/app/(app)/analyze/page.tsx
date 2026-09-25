"use client";
import Link from "next/link";
import { Suspense } from "react";
import { useSearchParams } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { ScanLine } from "lucide-react";
import { api } from "@/lib/api";
import { keys } from "@/lib/queries";
import { AnalyzeForm } from "@/components/analysis/analyze-form";
import { PageHeader } from "@/components/layout/page-header";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { PageSkeleton } from "@/components/ui/skeleton";

function AnalyzeContent() {
  const from = useSearchParams().get("from");
  const prev = useQuery({ queryKey: keys.analysis(from ?? ""), queryFn: () => api.analysis(from!), enabled: Boolean(from) });
  if (from && prev.isPending) return <PageSkeleton />;
  const initial = prev.data
    ? {
        ingredients_text: prev.data.raw_text,
        product_name: prev.data.product.name,
        brand: prev.data.product.brand ?? "",
        sodium: prev.data.sodium_mg_per_100g?.toString() ?? "",
      }
    : undefined;
  return (
    <Card>
      <CardContent className="pt-5 sm:pt-6">
        <AnalyzeForm key={from ?? "new"} initial={initial} showExamples={!from} />
      </CardContent>
    </Card>
  );
}

export default function AnalyzePage() {
  return (
    <div className="max-w-2xl">
      <PageHeader
        title="Manual analysis"
        description="Type or paste an ingredient list to get an instant score."
        actions={
          <Button asChild variant="outline" size="sm">
            <Link href="/scan"><ScanLine /> Scan instead</Link>
          </Button>
        }
      />
      <Suspense fallback={<PageSkeleton />}>
        <AnalyzeContent />
      </Suspense>
    </div>
  );
}
