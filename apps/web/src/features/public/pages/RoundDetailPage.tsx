import { Link, useParams } from "react-router-dom";
import { api } from "../../../api/client";
import { useApiResource } from "../../../app/useApiResource";
import { MatchCard } from "../../../components/MatchCard";
import { PageShell } from "../../../components/PageShell";
import { PublicTournamentTabs } from "../../../components/PublicTournamentTabs";
import { finalRoundLabel } from "../../tournaments/formatMeta";

export function RoundDetailPage() {
  const { slug, roundId } = useParams();
  const tournament = useApiResource(() => api.getPublicTournament(slug ?? ""), [slug]);
  const round = useApiResource(() => api.getPublicRound(slug ?? "", roundId ?? ""), [slug, roundId]);

  return (
    <PageShell
      mode="public"
      title={round.data?.name ?? "Round details"}
      subtitle={tournament.data ? `${tournament.data.name} · matches and results for this round` : undefined}
    >
      {tournament.loading || round.loading ? <div className="card">Loading round...</div> : null}
      {tournament.error || round.error ? <div className="card error-card">{tournament.error ?? round.error}</div> : null}
      {round.data ? (
        <section className="content-stack">
          {tournament.data ? <PublicTournamentTabs slug={tournament.data.slug} current="rounds" /> : null}
          <div className="card">
            <div className="card-header-row">
              <div>
                <h2>{round.data.name}</h2>
                <p className="muted-text">
                  {round.data.is_final
                    ? finalRoundLabel(tournament.data?.format)
                    : `Round ${round.data.number}`}
                </p>
              </div>
              {tournament.data ? (
                <div className="button-row compact-row">
                  <Link to={`/tournaments/${tournament.data.slug}`}>Tournament overview</Link>
                  <Link to={`/tournaments/${tournament.data.slug}/standings`}>Standings</Link>
                </div>
              ) : null}
            </div>
          </div>
          {round.data.matches.length ? (
            <div className="card-grid">
              {round.data.matches.map((match) => (
                <MatchCard key={match.id} match={match} publicLink={`/matches/${match.id}`} />
              ))}
            </div>
          ) : (
            <div className="card">No matches are assigned to this round yet.</div>
          )}
        </section>
      ) : null}
    </PageShell>
  );
}
