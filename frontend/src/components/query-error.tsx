"use client";
import Link from "next/link";
import { RefreshCw } from "lucide-react";
import { ApiError } from "@/lib/api";
import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";

export function QueryError({ error, onRetry }: { error: unknown; onRetry?: () => void }) {
  const notFound = error instanceof ApiError && error.status === 404;
  const message = error instanceof ApiError ? error.message : "Something went wrong while loading this page.";
  return (
    <Alert
      tone="error"
      title={notFound ? "Not found" : "Couldn't load this page"}
      action={
        notFound ? (
          <Button asChild variant="outline" size="sm"><Link href="/history">Go to history</Link></Button>
        ) : (
          onRetry && <Button variant="outline" size="sm" onClick={onRetry}><RefreshCw /> Try again</Button>
        )
      }
    >
      {message}
    </Alert>
  );
}
