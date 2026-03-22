import { FormEvent, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { api } from "../../../api/client";
import { PageShell } from "../../../components/PageShell";

export function PasswordResetPage() {
  const [searchParams] = useSearchParams();
  const token = searchParams.get("token")?.trim() ?? "";
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    if (submitting) return;

    if (!token) {
      setError("This password reset link is incomplete. Request a new email and try again.");
      return;
    }
    if (password.trim().length < 8) {
      setError("Password must be at least 8 characters.");
      return;
    }
    if (password !== confirmPassword) {
      setError("Passwords do not match.");
      return;
    }

    setSubmitting(true);
    setMessage(null);
    setError(null);
    try {
      const response = await api.confirmPasswordReset(token, password);
      setMessage(response.message);
      setPassword("");
      setConfirmPassword("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to reset password");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <PageShell mode="public" title="Reset password" subtitle="Choose a new password for your PodiumForge account using the secure email link you received.">
      <section className="card auth-card">
        {!token ? <div className="error-inline" role="alert">This password reset link is incomplete. Request a fresh email from the login page.</div> : null}
        {token ? (
          <form className="form-grid" onSubmit={handleSubmit}>
            <label>
              <span>New password</span>
              <input required minLength={8} type="password" value={password} onChange={(event) => setPassword(event.target.value)} />
            </label>
            <label>
              <span>Confirm new password</span>
              <input required minLength={8} type="password" value={confirmPassword} onChange={(event) => setConfirmPassword(event.target.value)} />
            </label>
            {message ? <div className="success-inline" role="status" aria-live="polite">{message} Use the button below to sign in.</div> : null}
            {error ? <div className="error-inline" role="alert">{error}</div> : null}
            <button type="submit" disabled={submitting}>
              {submitting ? "Updating..." : "Update password"}
            </button>
          </form>
        ) : null}
        <div className="seed-note">
          <Link to="/login">Back to login</Link>
        </div>
      </section>
    </PageShell>
  );
}
