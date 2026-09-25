import type { Metadata } from "next";
import { PageHeader } from "@/components/layout/page-header";
import { Scanner } from "@/components/scan/scanner";

export const metadata: Metadata = { title: "Scan product" };

export default function ScanPage() {
  return (
    <div>
      <PageHeader title="Scan product" description="Photograph the ingredient list — we'll read it and score it." />
      <Scanner />
    </div>
  );
}
