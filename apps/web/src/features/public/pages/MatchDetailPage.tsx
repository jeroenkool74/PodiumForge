import { useMemo } from "react";
import { Link, useParams } from "react-router-dom";
import { placementLabel } from "@podiumforge/shared";
import { api } from "../../../api/client";
import { useApiResource } from "../../../app/useApiResource";
import { PageShell } from "../../../components/PageShell";
import { StatusPill } from "../../../components/StatusPill";

export function MatchDetailPage() {
  const { matchId } = useParams();
  const { data, loading, error } = useApiResource(() => api.getPublicMatch(matchId ?? ""), [matchId]);
  const isBye = data?.is_bye;
  const orderedEntrants = useMemo(
    () => (data ? [...data.entrants].sort((left, right) => (left.rank ?? 999) - (right.rank ?? 999)) : []),
    [data],
  );

  return (
    <PageShell mode="public" title={data?.name ?? "Match details"} subtitle="Match placements, scores, and round context.">
      {loading ? <div className="card">Loading match...</div> : null}
      {error ? <div className="card error-card">{error}</div> : null}
      {data ? (
        <section className="card feature-card">
          <div className="card-header-row">
            <div>
              <h2>{data.name}</h2>
              <p className="muted-text">
                {isBye
                  ? "Automatic bye advancement with no manual result entry required."
                  : data.entrants.length === 2
                    ? "Head-to-head match view with seed, score, and winner tracking."
                    : `${data.entrants.length} entrants in this ranked match`}
              </p>
            </div>
            <div className="button-row compact-row">
              <StatusPill value={data.status} />
              <Link to={`/tournaments/${data.tournament_slug}`}>Tournament overview</Link>
              <Link to={`/tournaments/${data.tournament_slug}/rounds/${data.round_id}`}>{data.round_name}</Link>
            </div>
          </div>
          <div className="results-grid">
            {orderedEntrants.map((entrant) => (
              <div key={entrant.participant_id} className="result-row-card">
                <strong>{entrant.display_name}</strong>
                <span>{placementLabel(entrant.rank)}</span>
                <span className="muted-text">{entrant.points_awarded ?? 0} pts</span>
                <span className="muted-text">{isBye && entrant.seed_number ? `Seed #${entrant.seed_number}` : `Score ${entrant.score ?? "-"}`}</span>
              </div>
            ))}
          </div>
        </section>
      ) : null}
    </PageShell>
  );
}
