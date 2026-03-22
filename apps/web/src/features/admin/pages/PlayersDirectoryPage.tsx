import { FormEvent, useState } from "react";
import { api } from "../../../api/client";
import { useApiResource } from "../../../app/useApiResource";
import { PageShell } from "../../../components/PageShell";
import { useAuth } from "../../auth/AuthContext";

export function PlayersDirectoryPage() {
  const { token } = useAuth();
  const players = useApiResource(() => api.listDirectoryPlayers(token ?? ""), [token]);
  const [newName, setNewName] = useState("");
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editingName, setEditingName] = useState("");
  const [deleteId, setDeleteId] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function handleCreate(event: FormEvent) {
    event.preventDefault();
    if (!newName.trim() || saving) return;
    setSaving(true);
    setMessage(null);
    setError(null);
    try {
      await api.createDirectoryPlayer(token ?? "", { name: newName.trim() });
      setNewName("");
      setMessage("Player added to the directory.");
      await players.refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to add player");
    } finally {
      setSaving(false);
    }
  }

  async function handleSave(playerId: string) {
    if (!editingName.trim() || saving) return;
    setSaving(true);
    setMessage(null);
    setError(null);
    try {
      await api.updateDirectoryPlayer(token ?? "", playerId, { name: editingName.trim() });
      setEditingId(null);
      setEditingName("");
      setMessage("Player updated.");
      await players.refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to update player");
    } finally {
      setSaving(false);
    }
  }

  async function handleDelete(playerId: string) {
    if (saving) return;
    setSaving(true);
    setMessage(null);
    setError(null);
    try {
      await api.deleteDirectoryPlayer(token ?? "", playerId);
      setDeleteId(null);
      setMessage("Player removed from the directory.");
      await players.refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to delete player");
    } finally {
      setSaving(false);
    }
  }

  return (
    <PageShell
      mode="admin"
      title="Player directory"
      subtitle="Build a reusable player pool once, then seed tournaments from it whenever you need to."
    >
      {message ? <div className="success-inline">{message}</div> : null}
      {error ? <div className="error-inline">{error}</div> : null}

      <section className="card two-column-card">
        <form className="form-grid" onSubmit={handleCreate}>
          <h2>Add player</h2>
          <label>
            <span>Name</span>
            <input value={newName} onChange={(event) => setNewName(event.target.value)} placeholder="Add a reusable player" />
          </label>
          <button type="submit" disabled={saving || !newName.trim()}>{saving ? "Saving..." : "Add player"}</button>
        </form>

        <div className="content-stack">
          <div className="section-heading">
            <div>
              <h2>Available players</h2>
              <p className="muted-text">{players.data?.length ?? 0} players ready for tournament selection.</p>
            </div>
          </div>

          {players.loading ? <div className="card">Loading player directory...</div> : null}
          <div className="user-list">
            {players.data?.map((player) => (
              <article key={player.id} className="mini-card user-card">
                {editingId === player.id ? (
                  <div className="content-stack">
                    <label>
                      <span>Name</span>
                      <input value={editingName} onChange={(event) => setEditingName(event.target.value)} />
                    </label>
                    <div className="button-row compact-row">
                      <button type="button" onClick={() => void handleSave(player.id)} disabled={saving || !editingName.trim()}>{saving ? "Saving..." : "Save"}</button>
                      <button type="button" className="ghost-button" onClick={() => { setEditingId(null); setEditingName(""); }} disabled={saving}>Cancel</button>
                    </div>
                  </div>
                ) : deleteId === player.id ? (
                  <div className="content-stack">
                    <strong>{player.name}</strong>
                    <p className="muted-text">Delete this reusable player entry?</p>
                    <div className="button-row compact-row">
                      <button type="button" className="danger-button" onClick={() => void handleDelete(player.id)} disabled={saving}>{saving ? "Deleting..." : "Confirm"}</button>
                      <button type="button" className="ghost-button" onClick={() => setDeleteId(null)} disabled={saving}>Cancel</button>
                    </div>
                  </div>
                ) : (
                  <div className="card-header-row">
                    <strong>{player.name}</strong>
                    <div className="button-row compact-row">
                      <button type="button" className="ghost-button" onClick={() => { setEditingId(player.id); setEditingName(player.name); }}>Edit</button>
                      <button type="button" className="danger-button" onClick={() => setDeleteId(player.id)}>Delete</button>
                    </div>
                  </div>
                )}
              </article>
            ))}
            {!players.loading && !players.data?.length ? <div className="card">No players added yet.</div> : null}
          </div>
        </div>
      </section>
    </PageShell>
  );
}
