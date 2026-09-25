import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatPoints(points: number): string {
  if (points > 0) return `+${points}`;
  if (points < 0) return `−${Math.abs(points)}`;
  return "0";
}

export function formatDate(iso: string): string {
  return new Intl.DateTimeFormat(undefined, { dateStyle: "medium", timeStyle: "short" }).format(new Date(iso));
}

export function formatRelative(iso: string, now: Date = new Date()): string {
  const seconds = Math.round((now.getTime() - new Date(iso).getTime()) / 1000);
  if (seconds < 60) return "just now";
  const minutes = Math.round(seconds / 60);
  if (minutes < 60) return `${minutes} min ago`;
  const hours = Math.round(minutes / 60);
  if (hours < 24) return `${hours} h ago`;
  const days = Math.round(hours / 24);
  if (days < 7) return `${days} d ago`;
  return new Intl.DateTimeFormat(undefined, { dateStyle: "medium" }).format(new Date(iso));
}

export const PRODUCT_TYPE_LABELS: Record<string, string> = {
  soft_drink: "Soft drink", breakfast_cereal: "Breakfast cereal", snack_bar: "Snack bar",
  cookies: "Cookies & crackers", chips: "Chips & snacks", chocolate: "Chocolate & candy",
  yogurt: "Yogurt", bread: "Bread & wraps", noodles: "Noodles & pasta", sauce: "Sauces & spreads",
  ice_cream: "Ice cream", juice: "Juice", nut_butter: "Nut butter", other: "Packaged food",
};
