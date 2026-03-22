import { Link } from "react-router-dom";
import type { MatchRecord } from "../api/types";
import { StatusPill } from "./StatusPill";

interface MatchCardProps {
  match: MatchRecord;
  publicLink?: string;
  adminLink?: string;
}

export function MatchCard({ match, publicLink, adminLink }: MatchCardProps) {
  const isBye = match.is_bye;

  return (
    <article className="card match-card">
      <div className="card-header-row">
        <div>
          <h3>{match.name}</h3>
          <p className="muted-text">{isBye ? "Automatic bye advancement" : `${match.entrants.length} entrants`}</p>
        </div>
        <StatusPill value={match.status} />
      </div>
      <ol className="entrant-list">
        {match.entrants.map((entrant) => (
          <li key={entrant.participant_id}>
            <span>{entrant.display_name}</span>
            <span className="entrant-meta">
              {entrant.rank ? `#${entrant.rank}` : entrant.seed_number ? `Seed #${entrant.seed_number}` : `Slot ${entrant.slot_number}`}
              {entrant.points_awarded !== null ? ` · ${entrant.points_awarded} pts` : ""}
            </span>
          </li>
        ))}
      </ol>
      <div className="button-row compact-row">
        {publicLink ? <Link to={publicLink}>Public view</Link> : null}
        {adminLink && !isBye && !match.results_locked ? <Link to={adminLink}>Enter results</Link> : null}
        {adminLink && match.results_locked ? <span className="muted-text">Results locked</span> : null}
      </div>
    </article>
  );
}
