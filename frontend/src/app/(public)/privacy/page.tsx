import type { Metadata } from "next";
import { LegalPage } from "../legal";

export const metadata: Metadata = { title: "Privacy Policy" };

export default function PrivacyPage() {
  return (
    <LegalPage title="Privacy Policy" updated="September 2026">
      <section>
        <h2>What we collect</h2>
        <ul>
          <li>Account details: your email address, optional name and a securely hashed password.</li>
          <li>Analyses you run: ingredient text, product names, extracted label text, scores and timestamps.</li>
          <li>Label photos are processed to extract text and are <strong>not stored</strong> after processing.</li>
        </ul>
      </section>
      <section>
        <h2>How we use it</h2>
        <p>
          Only to provide the service: analyze ingredients, show your history, saved products and comparisons. We do not
          sell your data or use it for advertising.
        </p>
      </section>
      <section>
        <h2>AI processing</h2>
        <p>
          When AI features are enabled, label images and ingredient text are sent to our AI provider solely to read and
          classify ingredients. The AI does not decide your score — a fixed rule engine does.
        </p>
      </section>
      <section>
        <h2>Security</h2>
        <p>
          Passwords are hashed with bcrypt, sessions use secure HTTP-only cookies with CSRF protection, and all access to
          your data is restricted to your account.
        </p>
      </section>
      <section>
        <h2>Your choices</h2>
        <p>
          You can delete individual analyses at any time, and permanently delete your account and all associated data
          from your Profile page.
        </p>
      </section>
    </LegalPage>
  );
}
