import type { Metadata } from "next";
import { LegalPage } from "../legal";

export const metadata: Metadata = { title: "Terms of Service" };

export default function TermsPage() {
  return (
    <LegalPage title="Terms of Service" updated="September 2026">
      <section>
        <h2>Informational use only</h2>
        <p>
          GuessIngs provides an ingredient-based assessment to help you compare products. It is not medical, dietary or
          allergy advice. Always read the actual product label, and consult a qualified professional for health decisions.
        </p>
      </section>
      <section>
        <h2>Accuracy</h2>
        <p>
          Scores depend on the ingredient text provided or extracted from photos. Text recognition can make mistakes —
          please review extracted ingredients before analyzing. Scores use published, versioned rules.
        </p>
      </section>
      <section>
        <h2>Your account</h2>
        <ul>
          <li>Keep your password confidential; you are responsible for activity on your account.</li>
          <li>Don&apos;t misuse the service, attempt to access other users&apos; data, or overload it with automated requests.</li>
        </ul>
      </section>
      <section>
        <h2>Changes</h2>
        <p>We may update these terms and the scoring rules. Each analysis records the rule version used.</p>
      </section>
    </LegalPage>
  );
}
