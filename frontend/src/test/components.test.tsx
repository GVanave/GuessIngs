import { render, screen, within } from "@testing-library/react";
import { ScoreBreakdown } from "@/components/analysis/score-breakdown";
import { ScoreRing } from "@/components/analysis/score-ring";
import { ScorePill, VerdictBadge } from "@/components/analysis/verdict";
import { CategoryChip, categoryTone } from "@/components/analysis/category-chip";
import { BottomNav } from "@/components/layout/app-shell";
import { Alert } from "@/components/ui/alert";
import { Field } from "@/components/ui/field";
import type { ScoreLine } from "@/lib/types";

vi.mock("next/navigation", () => ({ usePathname: () => "/dashboard", useRouter: () => ({ replace: vi.fn(), push: vi.fn() }) }));

describe("VerdictBadge", () => {
  it.each(["GREEN", "YELLOW", "RED"] as const)("shows text and an icon for %s (not color alone)", (v) => {
    const { container } = render(<VerdictBadge verdict={v} showDescription />);
    expect(screen.getByText(v)).toBeInTheDocument();
    expect(container.querySelector("svg")).not.toBeNull();
    expect(container.firstChild).toHaveAttribute("data-verdict", v);
  });
});

describe("ScoreRing", () => {
  it("exposes an accessible label with score and verdict", () => {
    render(<ScoreRing score={82} verdict="GREEN" animate={false} />);
    expect(screen.getByRole("img")).toHaveAccessibleName(/Score 82 out of 100\. Verdict GREEN/);
    expect(screen.getByTestId("score-value")).toHaveTextContent("82");
  });
});

describe("ScorePill", () => {
  it("has an accessible label", () => {
    render(<ScorePill score={42} verdict="RED" />);
    expect(screen.getByLabelText("Score 42 out of 100, RED")).toBeInTheDocument();
  });
});

describe("ScoreBreakdown", () => {
  const lines: ScoreLine[] = [
    { code: "start", label: "Starting score", points: 100, detail: "", ingredients: [] },
    { code: "added_sugar", label: "Added sugar", points: -25, detail: "sugar is the 2nd ingredient", ingredients: ["sugar"] },
    { code: "preservative", label: "Preservative", points: -6, detail: "−6 each", ingredients: [] },
    { code: "fiber_protein", label: "Fiber source", points: 5, detail: "+5", ingredients: [] },
  ];
  it("renders every line with signed points and the final score", () => {
    render(<ScoreBreakdown lines={lines} score={74} />);
    const table = screen.getByRole("table", { name: "Score calculation" });
    expect(within(table).getByTestId("line-start")).toHaveTextContent("100");
    expect(within(table).getByTestId("line-added_sugar")).toHaveTextContent("−25");
    expect(within(table).getByTestId("line-preservative")).toHaveTextContent("−6");
    expect(within(table).getByTestId("line-fiber_protein")).toHaveTextContent("+5");
    expect(screen.getByTestId("final-score")).toHaveTextContent("74");
    expect(screen.getByText("sugar is the 2nd ingredient")).toBeInTheDocument();
  });
});

describe("CategoryChip", () => {
  it("marks tone with a symbol as well as color", () => {
    expect(categoryTone("preservative")).toBe("bad");
    expect(categoryTone("healthy_fat")).toBe("good");
    expect(categoryTone("culinary")).toBe("neutral");
    render(<CategoryChip category="added_sugar" label="Added sugar" />);
    expect(screen.getByText("Added sugar").parentElement ?? screen.getByText("Added sugar")).toHaveTextContent("−");
  });
});

describe("BottomNav", () => {
  it("shows the 5 mobile destinations with Scan as primary and marks the current page", () => {
    render(<BottomNav pathname="/history" />);
    const nav = screen.getByRole("navigation", { name: "Primary" });
    const links = within(nav).getAllByRole("link");
    expect(links.map((l) => l.textContent)).toEqual(["Home", "History", "Scan", "Saved", "Profile"]);
    expect(within(nav).getByRole("link", { name: "History" })).toHaveAttribute("aria-current", "page");
    expect(within(nav).getByRole("link", { name: "Scan" })).toHaveAttribute("href", "/scan");
  });
});

describe("Field", () => {
  it("wires labels, hints and errors for screen readers", () => {
    render(<Field id="email" label="Email" error="Enter a valid email address.">{(p) => <input {...p} />}</Field>);
    const input = screen.getByLabelText("Email");
    expect(input).toHaveAttribute("aria-invalid", "true");
    expect(input).toHaveAccessibleDescription("Enter a valid email address.");
    expect(screen.getByRole("alert")).toHaveTextContent("Enter a valid email address.");
  });
});

describe("Alert", () => {
  it("uses role=alert for errors and status otherwise", () => {
    const { rerender } = render(<Alert tone="error" title="Oops">Bad</Alert>);
    expect(screen.getByRole("alert")).toHaveTextContent("Oops");
    rerender(<Alert tone="info">Fine</Alert>);
    expect(screen.getByRole("status")).toHaveTextContent("Fine");
  });
});
