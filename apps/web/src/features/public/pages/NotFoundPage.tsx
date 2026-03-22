import { Link } from "react-router-dom";
import { PageShell } from "../../../components/PageShell";

export function NotFoundPage() {
  return (
    <PageShell mode="public" title="Page not found" subtitle="The page you opened does not exist, or the link is no longer valid.">
      <section className="card feature-card content-stack">
        <p>Try one of the main entry points to get back into the tournament flow.</p>
        <div className="button-row compact-row">
          <Link to="/">Go home</Link>
          <Link to="/login">Login</Link>
        </div>
      </section>
    </PageShell>
  );
}
