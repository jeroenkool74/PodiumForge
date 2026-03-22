import { Link } from "react-router-dom";
import { getParticipantTypeLabel, getTournamentFormatLabel } from "@podiumforge/shared";
import { api } from "../../../api/client";
import { PageShell } from "../../../components/PageShell";
import { StatusPill } from "../../../components/StatusPill";
import { TournamentSchemeLibrary } from "../../../components/TournamentSchemeLibrary";
import { useApiResource } from "../../../app/useApiResource";

export function HomePage() {
  const { data, loading, error } = useApiResource(() => api.listPublicTournaments(), []);

  return (
    <PageShell
      mode="public"
      title="Tournament dashboards"
      subtitle="Open a tournament to view its overview, standings, rounds, matches, and live dashboard."
    >
      <section className="content-stack">
        <div className="section-heading">
          <h2>Tournaments</h2>
        </div>

        {loading ? <div className="card">Loading tournaments...</div> : null}
        {error ? <div className="card error-card">{error}</div> : null}
        {!loading && !error && !data?.length ? <div className="card">No public tournaments are available yet.</div> : null}

        <div className="card-grid">
          {data?.map((tournament) => (
            <article key={tournament.id} className="card tournament-card">
              <div className="card-header-row">
                <div>
                  <span className="eyebrow">{getParticipantTypeLabel(tournament.participant_type)}</span>
                  <h3>{tournament.name}</h3>
                </div>
                <StatusPill value={tournament.status} />
              </div>
              <p>{tournament.description}</p>
              <dl className="meta-grid">
                <div>
                  <dt>Format</dt>
                  <dd>{getTournamentFormatLabel(tournament.format)}</dd>
                </div>
                <div>
                  <dt>Entrants</dt>
                  <dd>{tournament.participant_count}</dd>
                </div>
                <div>
                  <dt>Current round</dt>
                  <dd>{tournament.current_round_name ?? "Not started"}</dd>
                </div>
                <div>
                  <dt>Match size</dt>
                  <dd>{tournament.match_size ?? "-"}</dd>
                </div>
              </dl>
              <div className="button-row">
                <Link to={`/tournaments/${tournament.slug}`}>Overview</Link>
                <Link to={`/tournaments/${tournament.slug}/standings`}>Standings</Link>
                <Link to={`/dashboard/${tournament.slug}`}>Dashboard</Link>
              </div>
            </article>
          ))}
        </div>

        <TournamentSchemeLibrary />
      </section>
    </PageShell>
  );
}
