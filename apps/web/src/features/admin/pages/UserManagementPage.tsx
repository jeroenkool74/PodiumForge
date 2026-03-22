import { type FormEvent, useState } from "react";
import type { UserRecord } from "../../../api/types";
import { api } from "../../../api/client";
import { useApiResource } from "../../../app/useApiResource";
import { PageShell } from "../../../components/PageShell";
import { useAuth } from "../../auth/AuthContext";

function sortUsers(users: UserRecord[]) {
  return [...users].sort((left, right) => left.username.localeCompare(right.username));
}

export function UserManagementPage() {
  const { token, user: currentUser } = useAuth();
  const users = useApiResource(() => api.listUsers(token ?? ""), [token]);
  const [form, setForm] = useState({ username: "", email: "", password: "", admin: false, editor: true });
  const [passwordForm, setPasswordForm] = useState({ password: "", confirmPassword: "" });
  const [activePasswordUserId, setActivePasswordUserId] = useState<string | null>(null);
  const [editingRolesUserId, setEditingRolesUserId] = useState<string | null>(null);
  const [roleDraft, setRoleDraft] = useState<string[]>([]);
  const [deleteConfirmUserId, setDeleteConfirmUserId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [latestUserId, setLatestUserId] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [changingPasswordUserId, setChangingPasswordUserId] = useState<string | null>(null);
  const [savingRolesUserId, setSavingRolesUserId] = useState<string | null>(null);
  const [resettingPasswordUserId, setResettingPasswordUserId] = useState<string | null>(null);
  const [deletingUserId, setDeletingUserId] = useState<string | null>(null);

  function clearFeedback() {
    setError(null);
    setMessage(null);
  }

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    if (submitting) return;

    clearFeedback();

    const username = form.username.trim();
    const email = form.email.trim().toLowerCase();
    const password = form.password;
    const roles = [form.editor ? "TOURNAMENT_EDITOR" : null, form.admin ? "ADMIN" : null].filter(Boolean) as string[];

    if (username.length < 3) {
      setError("Username must be at least 3 characters.");
      return;
    }
    if (!email) {
      setError("Email is required.");
      return;
    }
    if (!email.includes("@")) {
      setError("Enter a valid email address.");
      return;
    }
    if (password.length < 8) {
      setError("Password must be at least 8 characters.");
      return;
    }
    if (!roles.length) {
      setError("Select at least one role.");
      return;
    }

    setSubmitting(true);
    try {
      const createdUser = await api.createUser(token ?? "", {
        username,
        email,
        password,
        roles,
      });

      users.mutate((current) => {
        const withoutDuplicate = (current ?? []).filter((user) => user.id !== createdUser.id);
        return sortUsers([...withoutDuplicate, createdUser]);
      });
      setLatestUserId(createdUser.id);
      setMessage(`Created ${createdUser.username}.`);
      setForm({ username: "", email: "", password: "", admin: false, editor: true });
      void users.refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to create user");
    } finally {
      setSubmitting(false);
    }
  }

  function openPasswordForm(userId: string) {
    clearFeedback();
    setDeleteConfirmUserId(null);
    setActivePasswordUserId((current) => {
      const next = current === userId ? null : userId;
      setPasswordForm({ password: "", confirmPassword: "" });
      return next;
    });
  }

  function openRolesForm(user: UserRecord) {
    clearFeedback();
    setActivePasswordUserId(null);
    setDeleteConfirmUserId(null);
    setEditingRolesUserId((current) => {
      if (current === user.id) {
        setRoleDraft([]);
        return null;
      }
      setRoleDraft(user.roles);
      return user.id;
    });
  }

  function toggleRole(role: string) {
    setRoleDraft((current) => current.includes(role) ? current.filter((item) => item !== role) : [...current, role]);
  }

  async function handleSaveRoles(user: UserRecord) {
    if (savingRolesUserId) return;
    clearFeedback();
    if (!roleDraft.length) {
      setError("Select at least one role.");
      return;
    }
    if (currentUser?.id === user.id && !roleDraft.includes("ADMIN")) {
      setError("You cannot remove your own admin role.");
      return;
    }
    setSavingRolesUserId(user.id);
    try {
      const updated = await api.updateUserRoles(token ?? "", user.id, { roles: roleDraft });
      users.mutate((current) => sortUsers((current ?? []).map((item) => item.id === updated.id ? updated : item)));
      setEditingRolesUserId(null);
      setRoleDraft([]);
      setMessage(`Roles updated for ${updated.username}.`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to update roles");
    } finally {
      setSavingRolesUserId(null);
    }
  }

  async function handlePasswordChange(event: FormEvent, user: UserRecord) {
    event.preventDefault();
    if (changingPasswordUserId) return;

    clearFeedback();

    if (passwordForm.password.trim().length < 8) {
      setError("Password must be at least 8 characters.");
      return;
    }
    if (passwordForm.password !== passwordForm.confirmPassword) {
      setError("Passwords do not match.");
      return;
    }

    setChangingPasswordUserId(user.id);
    try {
      await api.changeUserPassword(token ?? "", user.id, { password: passwordForm.password });
      setMessage(`Password updated for ${user.username}.`);
      setPasswordForm({ password: "", confirmPassword: "" });
      setActivePasswordUserId(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to change password");
    } finally {
      setChangingPasswordUserId(null);
    }
  }

  async function handlePasswordResetEmail(user: UserRecord) {
    if (resettingPasswordUserId) return;

    clearFeedback();
    setResettingPasswordUserId(user.id);
    try {
      await api.requestPasswordReset(user.email);
      setMessage(`Password reset email sent to ${user.email}.`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to send reset email");
    } finally {
      setResettingPasswordUserId(null);
    }
  }

  async function handleDeleteUser(user: UserRecord) {
    if (deletingUserId) return;

    clearFeedback();
    setDeletingUserId(user.id);
    try {
      await api.deleteUser(token ?? "", user.id);
      users.mutate((current) => sortUsers((current ?? []).filter((item) => item.id !== user.id)));
      if (latestUserId === user.id) {
        setLatestUserId(null);
      }
      if (activePasswordUserId === user.id) {
        setActivePasswordUserId(null);
      }
      setDeleteConfirmUserId(null);
      setMessage(`Deleted ${user.username}.`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to delete user");
    } finally {
      setDeletingUserId(null);
    }
  }

  return (
    <PageShell
      mode="admin"
      title="User management"
      subtitle="Create accounts, reset credentials, change passwords, and retire users with clear confirmation before destructive actions."
    >
      <section className="card two-column-card">
        {message ? (
          <div className="chip-panel success-panel full-width-row" role="status" aria-live="polite">
            <strong>Done</strong>
            <p>{message}</p>
          </div>
        ) : null}
        {error ? (
          <div className="chip-panel danger-panel full-width-row" role="alert">
            <strong>Attention</strong>
            <p>{error}</p>
          </div>
        ) : null}

        <form className="form-grid" onSubmit={handleSubmit}>
          <h2>Create account</h2>
          <label><span>Username</span><input required minLength={3} value={form.username} onChange={(event) => setForm((current) => ({ ...current, username: event.target.value }))} /></label>
          <label><span>Email</span><input required type="email" value={form.email} onChange={(event) => setForm((current) => ({ ...current, email: event.target.value }))} /></label>
          <label><span>Temporary password</span><input required minLength={8} type="password" value={form.password} onChange={(event) => setForm((current) => ({ ...current, password: event.target.value }))} /></label>
          <label className="checkbox-row"><input type="checkbox" checked={form.editor} onChange={(event) => setForm((current) => ({ ...current, editor: event.target.checked }))} />Tournament editor</label>
          <label className="checkbox-row"><input type="checkbox" checked={form.admin} onChange={(event) => setForm((current) => ({ ...current, admin: event.target.checked }))} />Admin</label>
          <button type="submit" disabled={submitting}>{submitting ? "Creating..." : "Create user"}</button>
        </form>

        <div className="content-stack">
          <div className="section-heading">
            <div>
              <h2>Existing users</h2>
              <p className="muted-text">{users.data?.length ?? 0} accounts available for admin access and tournament operations.</p>
            </div>
          </div>

          {users.loading ? <div className="card">Loading users...</div> : null}
          {users.error ? <div className="card error-card">{users.error}</div> : null}

          <div className="user-list">
            {users.data?.map((user) => {
              const isCurrentSession = currentUser?.id === user.id;
              const passwordFormOpen = activePasswordUserId === user.id;
              const roleFormOpen = editingRolesUserId === user.id;
              const deleteConfirmationOpen = deleteConfirmUserId === user.id;

              return (
                <article key={user.id} className={`mini-card user-card ${latestUserId === user.id ? "new-user-card" : ""}`}>
                  <div className="card-header-row">
                    <div>
                      <strong>{user.username}</strong>
                      <div className="muted-text">{user.email}</div>
                    </div>
                    <span className="muted-text">{user.is_active ? "Active" : "Inactive"}</span>
                  </div>

                  <div className="role-chip-row">
                    {user.roles.length ? user.roles.map((role) => <span key={role} className="role-chip">{role.replace(/_/g, " ")}</span>) : <span className="muted-text">No roles assigned</span>}
                  </div>

                  <div className="button-row compact-row">
                    <button type="button" className="ghost-button" onClick={() => openRolesForm(user)} disabled={Boolean(savingRolesUserId) || deletingUserId === user.id}>
                      {roleFormOpen ? "Close role editor" : "Edit roles"}
                    </button>
                    <button type="button" className="ghost-button" onClick={() => openPasswordForm(user.id)} disabled={Boolean(changingPasswordUserId) || deletingUserId === user.id}>
                      {passwordFormOpen ? "Close password form" : "Change password"}
                    </button>
                    <button type="button" className="ghost-button" onClick={() => void handlePasswordResetEmail(user)} disabled={Boolean(resettingPasswordUserId) || deletingUserId === user.id}>
                      {resettingPasswordUserId === user.id ? "Sending..." : "Send reset email"}
                    </button>
                    <button type="button" className="danger-button" onClick={() => setDeleteConfirmUserId((current) => current === user.id ? null : user.id)} disabled={isCurrentSession || Boolean(deletingUserId)}>
                      Delete user
                    </button>
                    {isCurrentSession ? <span className="muted-text">Current session cannot be deleted.</span> : null}
                  </div>

                  {roleFormOpen ? (
                    <div className="chip-panel inline-form-panel content-stack">
                      <div>
                        <strong>Edit roles for {user.username}</strong>
                        <p className="muted-text">Admins keep user management, while tournament editors can operate events and match entry.</p>
                      </div>
                      <label className="checkbox-row">
                        <input type="checkbox" checked={roleDraft.includes("ADMIN")} onChange={() => toggleRole("ADMIN")} disabled={isCurrentSession && roleDraft.includes("ADMIN") && roleDraft.length === 1} />
                        Admin
                      </label>
                      <label className="checkbox-row">
                        <input type="checkbox" checked={roleDraft.includes("TOURNAMENT_EDITOR")} onChange={() => toggleRole("TOURNAMENT_EDITOR")} />
                        Tournament editor
                      </label>
                      <div className="button-row compact-row">
                        <button type="button" onClick={() => void handleSaveRoles(user)} disabled={savingRolesUserId === user.id}>{savingRolesUserId === user.id ? "Saving..." : "Save roles"}</button>
                        <button type="button" className="ghost-button" onClick={() => setEditingRolesUserId(null)} disabled={savingRolesUserId === user.id}>Cancel</button>
                      </div>
                    </div>
                  ) : null}

                  {passwordFormOpen ? (
                    <form className="form-grid chip-panel inline-form-panel" onSubmit={(event) => void handlePasswordChange(event, user)}>
                      <div>
                        <strong>Change password for {user.username}</strong>
                        <p className="muted-text">The old password stops working immediately after you save this change.</p>
                      </div>
                      <label><span>New password</span><input required minLength={8} type="password" value={passwordForm.password} onChange={(event) => setPasswordForm((current) => ({ ...current, password: event.target.value }))} /></label>
                      <label><span>Confirm new password</span><input required minLength={8} type="password" value={passwordForm.confirmPassword} onChange={(event) => setPasswordForm((current) => ({ ...current, confirmPassword: event.target.value }))} /></label>
                      <div className="button-row compact-row">
                        <button type="submit" disabled={changingPasswordUserId === user.id}>{changingPasswordUserId === user.id ? "Saving..." : "Save new password"}</button>
                        <button type="button" className="ghost-button" onClick={() => setActivePasswordUserId(null)} disabled={changingPasswordUserId === user.id}>Cancel</button>
                      </div>
                    </form>
                  ) : null}

                  {deleteConfirmationOpen ? (
                    <div className="chip-panel danger-panel confirmation-panel">
                      <strong>Delete {user.username}?</strong>
                      <p>This action cannot be undone. Their login stops working immediately, but existing tournaments remain in place.</p>
                      <div className="button-row compact-row">
                        <button type="button" className="danger-button" onClick={() => void handleDeleteUser(user)} disabled={deletingUserId === user.id}>{deletingUserId === user.id ? "Deleting..." : "Confirm delete"}</button>
                        <button type="button" className="ghost-button" onClick={() => setDeleteConfirmUserId(null)} disabled={deletingUserId === user.id}>Cancel</button>
                      </div>
                    </div>
                  ) : null}
                </article>
              );
            })}
          </div>
        </div>
      </section>
    </PageShell>
  );
}
