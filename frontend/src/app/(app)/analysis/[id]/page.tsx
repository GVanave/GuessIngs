"use client";
import Link from "next/link";
import { use } from "react";
import { useQuery } from "@tanstack/react-query";
import { ArrowLeft } from "lucide-react";
import { api } from "@/lib/api";
import { keys } from "@/lib/queries";
import { ResultView } from "@/components/analysis/result-view";
import { QueryError } from "@/components/query-error";
import { PageSkeleton } from "@/components/ui/skeleton";

export default function AnalysisPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const q = useQuery({ queryKey: keys.analysis(id), queryFn: () => api.analysis(id) });
  return (
    <div>
      <Link href="/history" className="mb-4 inline-flex items-center gap-1.5 text-sm font-medium text-muted hover:text-foreground">
        <ArrowLeft className="size-4" aria-hidden /> History
      </Link>
      {q.isPending ? <PageSkeleton /> : q.isError ? <QueryError error={q.error} onRetry={() => q.refetch()} /> : <ResultView analysis={q.data} />}
    </div>
  );
}
