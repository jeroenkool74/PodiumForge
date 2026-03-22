import { Link } from "react-router-dom";
import { getTournamentFormatLabel } from "@podiumforge/shared";
import { api } from "../../../api/client";
import { useApiResource } from "../../../app/useApiResource";
import { PageShell } from "../../../components/PageShell";
import { StatusPill } from "../../../components/StatusPill";
import { useAuth } from "../../auth/AuthContext";
import { canManageUsers } from "../../auth/permissions";

export function AdminHomePage() {
  const { token, user } = useAuth();
  const dashboard = useApiResource(() => api.getAdminDashboard(token ?? ""), [token]);
  const tournaments = useApiResource(() => api.listManagedTournaments(token ?? ""), [token]);
  const loading = (dashboard.loading && !dashboard.data) || (tournaments.loading && !tournaments.data);
  const showUsers = canManageUsers(user);

  return (
    <PageShell mode="admin" title="Admin dashboard" subtitle="Operations overview for active tournaments, live rounds, and result entry shortcuts.">
      {loading ? <div className="card">Loading admin dashboard...</div> : null}
      <section className="card-grid metric-grid">
        <article className="card metric-card"><span className="eyebrow">Tournaments</span><strong>{dashboard.data?.tournaments ?? "-"}</strong></article>
        <article className="card metric-card"><span className="eyebrow">Live</span><strong>{dashboard.data?.live_tournaments ?? "-"}</strong></article>
        {showUsers ? <article className="card metric-card"><span className="eyebrow">Users</span><strong>{dashboard.data?.users ?? "-"}</strong></article> : null}
        <article className="card metric-card"><span className="eyebrow">Completed matches</span><strong>{dashboard.data?.completed_matches ?? "-"}</strong></article>
      </section>

      {dashboard.error || tournaments.error ? <div className="card error-card">{dashboard.error ?? tournaments.error}</div> : null}

      <section className="card">
        <div className="card-header-row">
          <div>
            <h2>Managed tournaments</h2>
            <p className="muted-text">Open a tournament, inspect rounds, or jump straight to result entry.</p>
          </div>
          <div className="button-row compact-row">
            <Link to="/admin/players">Players</Link>
            <Link to="/admin/teams">Teams</Link>
            <Link to="/admin/tournaments/new">Create tournament</Link>
          </div>
        </div>
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Name</th>
                <th>Format</th>
                <th>Round</th>
                <th>Status</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {tournaments.data?.map((tournament) => (
                <tr key={tournament.id}>
                  <td>{tournament.name}</td>
                  <td>{getTournamentFormatLabel(tournament.format)}</td>
                  <td>{tournament.current_round_name ?? "-"}</td>
                  <td><StatusPill value={tournament.status} /></td>
                  <td>
                    <div className="button-row compact-row">
                      <Link to={`/admin/tournaments/${tournament.id}`}>Manage</Link>
                      {tournament.is_public ? <Link to={`/tournaments/${tournament.slug}`}>Public</Link> : <span className="muted-text">Private</span>}
                    </div>
                  </td>
                </tr>
              ))}
              {!tournaments.loading && !tournaments.data?.length ? (
                <tr>
                  <td colSpan={5} className="muted-text">No tournaments yet. Create one to start running matches and public dashboards.</td>
                </tr>
              ) : null}
            </tbody>
          </table>
        </div>
      </section>
    </PageShell>
  );
}
