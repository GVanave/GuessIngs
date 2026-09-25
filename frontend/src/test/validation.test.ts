import { analyzeSchema, fieldErrors, loginSchema, registerSchema, validateImageFile } from "@/lib/validation";

describe("registerSchema", () => {
  it("accepts a valid registration", () => {
    expect(registerSchema.safeParse({ full_name: "Ada", email: "ada@example.com", password: "Passw0rd" }).success).toBe(true);
  });
  it.each([
    ["short", "at least 8"],
    ["longpassword", "number"],
    ["1234567890", "letter"],
  ])("rejects weak password %s", (password, message) => {
    const r = registerSchema.safeParse({ full_name: "", email: "a@b.co", password });
    expect(r.success).toBe(false);
    if (!r.success) expect(fieldErrors(r.error).password).toContain(message);
  });
  it("rejects invalid email", () => {
    const r = loginSchema.safeParse({ email: "nope", password: "x" });
    expect(r.success).toBe(false);
    if (!r.success) expect(fieldErrors(r.error).email).toMatch(/valid email/);
  });
});

describe("analyzeSchema", () => {
  it("requires ingredients", () => {
    const r = analyzeSchema.safeParse({ ingredients_text: "   ", sodium: "" });
    expect(r.success).toBe(false);
    if (!r.success) expect(fieldErrors(r.error).ingredients_text).toBe("Enter the ingredient list.");
  });
  it("rejects text without letters", () => {
    expect(analyzeSchema.safeParse({ ingredients_text: "123, 456", sodium: "" }).success).toBe(false);
  });
  it("validates sodium", () => {
    expect(analyzeSchema.safeParse({ ingredients_text: "oats", sodium: "450" }).success).toBe(true);
    expect(analyzeSchema.safeParse({ ingredients_text: "oats", sodium: "-3" }).success).toBe(false);
    expect(analyzeSchema.safeParse({ ingredients_text: "oats", sodium: "lots" }).success).toBe(false);
  });
});

describe("validateImageFile", () => {
  it("accepts images and rejects other types and sizes", () => {
    expect(validateImageFile(new File(["x"], "a.jpg", { type: "image/jpeg" }))).toBeNull();
    expect(validateImageFile(new File(["x"], "a.gif", { type: "image/gif" }))).toMatch(/JPG, PNG or WEBP/);
    expect(validateImageFile(new File([], "a.png", { type: "image/png" }))).toMatch(/empty/);
    const big = new File([new Uint8Array(9 * 1024 * 1024)], "big.png", { type: "image/png" });
    expect(validateImageFile(big)).toMatch(/8 MB/);
  });
});
