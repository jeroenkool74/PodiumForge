import { FormEvent, useEffect, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { api } from "../../../api/client";
import { PageShell } from "../../../components/PageShell";
import { useAuth } from "../../auth/AuthContext";

export function LoginPage() {
  const navigate = useNavigate();
  const location = useLocation();
  const { isAuthenticated, login, ready } = useAuth();
  const [loginValue, setLoginValue] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [resetEmail, setResetEmail] = useState("");
  const [resetMessage, setResetMessage] = useState<string | null>(null);
  const [resetError, setResetError] = useState<string | null>(null);
  const [resetSubmitting, setResetSubmitting] = useState(false);

  useEffect(() => {
    if (!ready || !isAuthenticated) return;
    const next = (location.state as { from?: string } | null)?.from ?? "/admin";
    navigate(next, { replace: true });
  }, [isAuthenticated, location.state, navigate, ready]);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    if (submitting) return;

    const normalizedLogin = loginValue.trim();
    if (!normalizedLogin) {
      setError("Enter your email or username.");
      return;
    }
    if (!password.trim()) {
      setError("Enter your password.");
      return;
    }

    setSubmitting(true);
    setError(null);
    try {
      await login(normalizedLogin, password);
      const next = (location.state as { from?: string } | null)?.from ?? "/admin";
      navigate(next, { replace: true });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Login failed");
    } finally {
      setSubmitting(false);
    }
  }

  async function handlePasswordResetRequest(event: FormEvent) {
    event.preventDefault();
    if (resetSubmitting) return;

    const normalizedEmail = resetEmail.trim().toLowerCase();
    if (!normalizedEmail) {
      setResetError("Enter the email address tied to the account.");
      return;
    }
    if (!normalizedEmail.includes("@")) {
      setResetError("Enter a valid email address.");
      return;
    }

    setResetSubmitting(true);
    setResetMessage(null);
    setResetError(null);
    try {
      const response = await api.requestPasswordReset(normalizedEmail);
      setResetMessage(response.message);
    } catch (err) {
      setResetError(err instanceof Error ? err.message : "Unable to send reset email");
    } finally {
      setResetSubmitting(false);
    }
  }

  return (
    <PageShell mode="public" title="Login" subtitle="Sign in to manage tournaments, users, and results.">
      <section className="two-column-card">
        <div className="card auth-card">
          <form className="form-grid" onSubmit={handleSubmit}>
            <h2>Sign in</h2>
            <label>
              <span>Email or username</span>
              <input required value={loginValue} onChange={(event) => setLoginValue(event.target.value)} />
            </label>
            <label>
              <span>Password</span>
              <input required type="password" value={password} onChange={(event) => setPassword(event.target.value)} />
            </label>
            {error ? <div className="error-inline" role="alert">{error}</div> : null}
            <button type="submit" disabled={submitting}>
              {submitting ? "Signing in..." : "Sign in"}
            </button>
          </form>
        </div>

        <div className="card auth-card">
          <form className="form-grid" onSubmit={handlePasswordResetRequest}>
            <h2>Password reset</h2>
            <p className="muted-text">Request a reset link by email. The link opens a dedicated password reset screen and expires automatically.</p>
            <label>
              <span>Account email</span>
              <input required type="email" value={resetEmail} onChange={(event) => setResetEmail(event.target.value)} />
            </label>
            {resetMessage ? <div className="success-inline" role="status" aria-live="polite">{resetMessage}</div> : null}
            {resetError ? <div className="error-inline" role="alert">{resetError}</div> : null}
            <button type="submit" disabled={resetSubmitting}>
              {resetSubmitting ? "Sending..." : "Send reset link"}
            </button>
          </form>
        </div>
      </section>
    </PageShell>
  );
}
