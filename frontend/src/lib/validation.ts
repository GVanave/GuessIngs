import { z } from "zod";

export const passwordSchema = z
  .string()
  .min(8, "Password must be at least 8 characters.")
  .max(128, "Password must be at most 128 characters.")
  .regex(/[A-Za-z]/, "Password must contain a letter.")
  .regex(/\d/, "Password must contain a number.");

export const registerSchema = z.object({
  full_name: z.string().trim().max(120, "Name is too long."),
  email: z.string().trim().email("Enter a valid email address."),
  password: passwordSchema,
});

export const loginSchema = z.object({
  email: z.string().trim().email("Enter a valid email address."),
  password: z.string().min(1, "Enter your password."),
});

export const analyzeSchema = z.object({
  ingredients_text: z
    .string()
    .trim()
    .min(1, "Enter the ingredient list.")
    .max(5000, "The ingredient list is too long (max 5,000 characters).")
    .refine((v) => /[a-zA-Z]{2,}/.test(v), "That doesn't look like an ingredient list."),
  product_name: z.string().trim().max(160, "Product name is too long.").optional(),
  sodium: z
    .string()
    .trim()
    .optional()
    .refine((v) => !v || (/^\d+(\.\d+)?$/.test(v) && Number(v) <= 40000), "Enter sodium in mg (e.g. 450)."),
});

export type FieldErrors = Record<string, string>;

export function fieldErrors(error: z.ZodError): FieldErrors {
  const out: FieldErrors = {};
  for (const issue of error.issues) {
    const key = String(issue.path[0] ?? "form");
    if (!out[key]) out[key] = issue.message;
  }
  return out;
}

export const ACCEPTED_IMAGE_TYPES = ["image/jpeg", "image/png", "image/webp"];
export const MAX_UPLOAD_BYTES = 8 * 1024 * 1024;

export function validateImageFile(file: File): string | null {
  if (!ACCEPTED_IMAGE_TYPES.includes(file.type)) return "Please choose a JPG, PNG or WEBP photo.";
  if (file.size > MAX_UPLOAD_BYTES) return "That photo is larger than 8 MB. Try a smaller image.";
  if (file.size === 0) return "That file is empty.";
  return null;
}
