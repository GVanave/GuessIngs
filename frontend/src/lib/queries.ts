"use client";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "./api";

export const keys = {
  me: ["me"] as const,
  dashboard: ["dashboard"] as const,
  history: (p: object) => ["history", p] as const,
  analysis: (id: string) => ["analysis", id] as const,
  saved: ["saved"] as const,
  compare: (ids: string[]) => ["compare", ...ids] as const,
};

export function useMe() {
  return useQuery({ queryKey: keys.me, queryFn: api.me, staleTime: 60_000 });
}

export function useToggleSave() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ productId, saved }: { productId: string; saved: boolean }) =>
      api.updateProduct(productId, { is_saved: saved }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["analysis"] });
      qc.invalidateQueries({ queryKey: keys.saved });
      qc.invalidateQueries({ queryKey: keys.dashboard });
    },
  });
}
