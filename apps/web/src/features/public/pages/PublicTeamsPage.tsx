import { useParams } from "react-router-dom";
import { api } from "../../../api/client";
import { useApiResource } from "../../../app/useApiResource";
import { PageShell } from "../../../components/PageShell";
import { PublicTournamentTabs } from "../../../components/PublicTournamentTabs";

export function PublicTeamsPage() {
  const { slug } = useParams();
  const teams = useApiResource(() => api.getPublicTeams(slug ?? ""), [slug]);

  return (
    <PageShell
      mode="public"
      title={teams.data ? `${teams.data.tournament_name} teams` : "Teams"}
      subtitle="Reusable team rosters and their player lineups for this tournament."
    >
      {teams.loading ? <div className="card">Loading teams...</div> : null}
      {teams.error ? <div className="card error-card">{teams.error}</div> : null}
      {teams.data ? (
        <>
          <PublicTournamentTabs slug={slug ?? ""} current="teams" showTeams />
          <section className="card-grid">
            {teams.data.teams.map((team) => (
              <article key={team.id} className="card team-card">
                <div className="card-header-row">
                  <div>
                    <span className="eyebrow">Team</span>
                    <h2>{team.name}</h2>
                  </div>
                  <span className="muted-text">{team.members.length} members</span>
                </div>
                {team.members.length ? (
                  <ul className="member-list">
                    {team.members.map((member) => (
                      <li key={`${team.id}-${member}`}>{member}</li>
                    ))}
                  </ul>
                ) : (
                  <p className="muted-text">No roster members stored for this team yet.</p>
                )}
              </article>
            ))}
            {!teams.data.teams.length ? (
              <article className="card">
                <h2>No teams published yet</h2>
                <p className="muted-text">This team tournament has no roster cards available yet.</p>
              </article>
            ) : null}
          </section>
        </>
      ) : null}
    </PageShell>
  );
}
