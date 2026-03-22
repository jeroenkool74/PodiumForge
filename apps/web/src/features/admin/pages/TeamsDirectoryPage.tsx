import { FormEvent, useMemo, useState } from "react";
import { api } from "../../../api/client";
import { useApiResource } from "../../../app/useApiResource";
import { PageShell } from "../../../components/PageShell";
import { useAuth } from "../../auth/AuthContext";

function toggleSelection(values: string[], value: string) {
  return values.includes(value) ? values.filter((item) => item !== value) : [...values, value];
}

export function TeamsDirectoryPage() {
  const { token } = useAuth();
  const directory = useApiResource(async () => ({
    players: await api.listDirectoryPlayers(token ?? ""),
    teams: await api.listDirectoryTeams(token ?? ""),
  }), [token]);

  const players = directory.data?.players ?? [];
  const teams = directory.data?.teams ?? [];
  const [newName, setNewName] = useState("");
  const [newPlayerIds, setNewPlayerIds] = useState<string[]>([]);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editingName, setEditingName] = useState("");
  const [editingPlayerIds, setEditingPlayerIds] = useState<string[]>([]);
  const [deleteId, setDeleteId] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const sortedPlayers = useMemo(() => [...players].sort((left, right) => left.name.localeCompare(right.name)), [players]);

  async function handleCreate(event: FormEvent) {
    event.preventDefault();
    if (!newName.trim() || saving) return;
    setSaving(true);
    setMessage(null);
    setError(null);
    try {
      await api.createDirectoryTeam(token ?? "", { name: newName.trim(), player_ids: newPlayerIds });
      setNewName("");
      setNewPlayerIds([]);
      setMessage("Team added to the directory.");
      await directory.refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to add team");
    } finally {
      setSaving(false);
    }
  }

  async function handleSave(teamId: string) {
    if (!editingName.trim() || saving) return;
    setSaving(true);
    setMessage(null);
    setError(null);
    try {
      await api.updateDirectoryTeam(token ?? "", teamId, { name: editingName.trim(), player_ids: editingPlayerIds });
      setEditingId(null);
      setEditingName("");
      setEditingPlayerIds([]);
      setMessage("Team updated.");
      await directory.refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to update team");
    } finally {
      setSaving(false);
    }
  }

  async function handleDelete(teamId: string) {
    if (saving) return;
    setSaving(true);
    setMessage(null);
    setError(null);
    try {
      await api.deleteDirectoryTeam(token ?? "", teamId);
      setDeleteId(null);
      setMessage("Team removed from the directory.");
      await directory.refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to delete team");
    } finally {
      setSaving(false);
    }
  }

  return (
    <PageShell
      mode="admin"
      title="Team directory"
      subtitle="Assemble reusable rosters from the player overview, then use those teams in team tournaments and public roster pages."
    >
      {message ? <div className="success-inline">{message}</div> : null}
      {error ? <div className="error-inline">{error}</div> : null}

      <section className="card two-column-card">
        <form className="form-grid" onSubmit={handleCreate}>
          <h2>Create team</h2>
          <label>
            <span>Team name</span>
            <input value={newName} onChange={(event) => setNewName(event.target.value)} placeholder="Add a reusable team" />
          </label>
          <div className="content-stack">
            <span>Members</span>
            <div className="directory-member-grid">
              {sortedPlayers.map((player) => (
                <label key={player.id} className="directory-member-option">
                  <input type="checkbox" checked={newPlayerIds.includes(player.id)} onChange={() => setNewPlayerIds((current) => toggleSelection(current, player.id))} />
                  <span>{player.name}</span>
                </label>
              ))}
            </div>
          </div>
          <button type="submit" disabled={saving || !newName.trim()}>{saving ? "Saving..." : "Create team"}</button>
        </form>

        <div className="content-stack">
          <div className="section-heading">
            <div>
              <h2>Available teams</h2>
              <p className="muted-text">{teams.length} reusable team lineups.</p>
            </div>
          </div>

          {directory.loading ? <div className="card">Loading team directory...</div> : null}
          <div className="card-grid">
            {teams.map((team) => (
              <article key={team.id} className="card team-card">
                {editingId === team.id ? (
                  <div className="content-stack">
                    <label>
                      <span>Team name</span>
                      <input value={editingName} onChange={(event) => setEditingName(event.target.value)} />
                    </label>
                    <div className="directory-member-grid">
                      {sortedPlayers.map((player) => (
                        <label key={`${team.id}-${player.id}`} className="directory-member-option">
                          <input type="checkbox" checked={editingPlayerIds.includes(player.id)} onChange={() => setEditingPlayerIds((current) => toggleSelection(current, player.id))} />
                          <span>{player.name}</span>
                        </label>
                      ))}
                    </div>
                    <div className="button-row compact-row">
                      <button type="button" onClick={() => void handleSave(team.id)} disabled={saving || !editingName.trim()}>{saving ? "Saving..." : "Save"}</button>
                      <button type="button" className="ghost-button" onClick={() => { setEditingId(null); setEditingName(""); setEditingPlayerIds([]); }} disabled={saving}>Cancel</button>
                    </div>
                  </div>
                ) : deleteId === team.id ? (
                  <div className="content-stack">
                    <strong>{team.name}</strong>
                    <p className="muted-text">Delete this reusable team entry?</p>
                    <div className="button-row compact-row">
                      <button type="button" className="danger-button" onClick={() => void handleDelete(team.id)} disabled={saving}>{saving ? "Deleting..." : "Confirm"}</button>
                      <button type="button" className="ghost-button" onClick={() => setDeleteId(null)} disabled={saving}>Cancel</button>
                    </div>
                  </div>
                ) : (
                  <div className="content-stack">
                    <div className="card-header-row">
                      <div>
                        <span className="eyebrow">Team</span>
                        <h2>{team.name}</h2>
                      </div>
                      <div className="button-row compact-row">
                        <button type="button" className="ghost-button" onClick={() => { setEditingId(team.id); setEditingName(team.name); setEditingPlayerIds(team.members.map((member) => member.id)); }}>Edit</button>
                        <button type="button" className="danger-button" onClick={() => setDeleteId(team.id)}>Delete</button>
                      </div>
                    </div>
                    {team.members.length ? (
                      <ul className="member-list">
                        {team.members.map((member) => <li key={`${team.id}-${member.id}`}>{member.name}</li>)}
                      </ul>
                    ) : (
                      <p className="muted-text">No members selected yet.</p>
                    )}
                  </div>
                )}
              </article>
            ))}
            {!directory.loading && !teams.length ? <div className="card">No teams added yet.</div> : null}
          </div>
        </div>
      </section>
    </PageShell>
  );
}
