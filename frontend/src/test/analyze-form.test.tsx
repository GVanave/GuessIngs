import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { AnalyzeForm } from "@/components/analysis/analyze-form";

const push = vi.fn();
vi.mock("next/navigation", () => ({ useRouter: () => ({ push, replace: vi.fn() }) }));

function setup(props = {}) {
  const qc = new QueryClient();
  return render(<QueryClientProvider client={qc}><AnalyzeForm showExamples {...props} /></QueryClientProvider>);
}

afterEach(() => { vi.unstubAllGlobals(); push.mockReset(); });

describe("AnalyzeForm", () => {
  it("shows a validation error on empty submit without calling the API", async () => {
    const f = vi.fn();
    vi.stubGlobal("fetch", f);
    setup();
    await userEvent.click(screen.getByRole("button", { name: "Analyze ingredients" }));
    expect(await screen.findByText("Enter the ingredient list.")).toBeInTheDocument();
    expect(screen.getByLabelText("Ingredients")).toHaveAttribute("aria-invalid", "true");
    expect(f).not.toHaveBeenCalled();
  });

  it("fills an example and navigates to the result on success", async () => {
    const f = vi.fn().mockResolvedValue(new Response(JSON.stringify({ id: "abc" }), { status: 201 }));
    vi.stubGlobal("fetch", f);
    setup();
    await userEvent.click(screen.getByRole("button", { name: /Trail Mix/ }));
    expect(screen.getByLabelText(/Product name/)).toHaveValue("Trail Mix");
    await userEvent.type(screen.getByLabelText(/Sodium/), "120");
    await userEvent.click(screen.getByRole("button", { name: "Analyze ingredients" }));
    await vi.waitFor(() => expect(push).toHaveBeenCalledWith("/analysis/abc"));
    const body = JSON.parse(f.mock.calls[0][1].body);
    expect(body).toMatchObject({ product_name: "Trail Mix", sodium_mg_per_100g: 120, source: "manual" });
  });

  it("shows server-side ingredient errors next to the field", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(JSON.stringify({ error: { code: "no_ingredients", message: "We couldn't find any ingredients in that text." } }), { status: 422 })));
    setup();
    await userEvent.type(screen.getByLabelText("Ingredients"), "zz qq");
    await userEvent.click(screen.getByRole("button", { name: "Analyze ingredients" }));
    expect(await screen.findByText("We couldn't find any ingredients in that text.")).toBeInTheDocument();
  });

  it("shows a recoverable error when the network fails", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new TypeError("offline")));
    setup();
    await userEvent.type(screen.getByLabelText("Ingredients"), "oats, salt");
    await userEvent.click(screen.getByRole("button", { name: "Analyze ingredients" }));
    expect(await screen.findByRole("alert")).toHaveTextContent(/couldn't reach the server/);
    expect(screen.getByRole("button", { name: "Analyze ingredients" })).toBeEnabled();
  });
});
