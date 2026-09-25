import { VerdictBadge } from "@/components/analysis/verdict";

const DEDUCTIONS = [
  ["Added sugar / syrups", "−15 to −30", "Set by the earliest sugar's position: 1st −30 · 2nd–3rd −25 · 4th–5th −20 · 6th+ −15. −5 per extra sugar source. Max −30."],
  ["Artificial sweetener", "−10 each", "Sucralose, aspartame, acesulfame K, sugar alcohols…"],
  ["Hydrogenated oil", "−25", "Hydrogenated or partially hydrogenated fats (trans fats)."],
  ["Artificial color", "−8 each", "Red 40, Yellow 5, caramel color, titanium dioxide…"],
  ["Artificial flavor", "−8 each", "Artificial flavors and enhancers such as MSG."],
  ["Preservative", "−6 each", "Sodium benzoate, potassium sorbate, BHA/BHT, nitrites…"],
  ["Emulsifier / ultra-processed marker", "−5 each", "Emulsifiers, gums, modified starch, protein isolates…"],
  ["High sodium", "−10", "Only when sodium is provided and exceeds 600 mg per 100 g."],
  ["Ultra-processed (NOVA 4)", "−20", "Any sweetener, hydrogenated oil, artificial color/flavor or emulsifier marker."],
];
const ADDITIONS = [
  ["Whole-food fiber/protein source", "+5 each, max +10", "Whole grains, legumes, nuts, seeds, dairy, eggs — within the first 5 ingredients."],
  ["Healthy fat source", "+5", "Olive, avocado or canola oil, nuts, seeds — within the first 5 ingredients."],
];

function RuleTable({ caption, rows }: { caption: string; rows: string[][] }) {
  return (
    <div className="mt-6 overflow-hidden rounded-2xl border border-border bg-surface">
      <table className="w-full text-left text-sm">
        <caption className="border-b border-border px-5 py-3 text-left font-semibold">{caption}</caption>
        <thead className="sr-only">
          <tr><th scope="col">Rule</th><th scope="col">Points</th><th scope="col">Details</th></tr>
        </thead>
        <tbody className="divide-y divide-border">
          {rows.map(([rule, points, detail]) => (
            <tr key={rule} className="align-top">
              <th scope="row" className="w-1/3 px-5 py-3 font-medium">{rule}</th>
              <td className="whitespace-nowrap px-2 py-3 font-mono font-semibold tabular">{points}</td>
              <td className="hidden px-5 py-3 text-muted sm:table-cell">{detail}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export function ScoringRulesTable() {
  return (
    <div>
      <RuleTable caption="Deductions" rows={DEDUCTIONS} />
      <RuleTable caption="Additions" rows={ADDITIONS} />
      <div className="mt-6 grid gap-3 sm:grid-cols-3">
        {([["GREEN", "80–100"], ["YELLOW", "50–79"], ["RED", "0–49"]] as const).map(([v, range]) => (
          <div key={v} className="flex items-center justify-between rounded-2xl border border-border bg-surface p-4">
            <VerdictBadge verdict={v} />
            <span className="font-mono text-sm font-semibold tabular">{range}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
