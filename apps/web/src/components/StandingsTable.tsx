import type { StandingEntry } from "../api/types";
import { leaderboardMetricLabel, scoreDirectionLabel, tieBreakLabel } from "../features/tournaments/formatMeta";
import { hasLiveStandings, standingPositionLabel } from "../features/tournaments/standingPresentation";
import { StatusPill } from "./StatusPill";

function nameSummary(entries: StandingEntry[]) {
  if (!entries.length) return "Nobody yet.";
  const preview = entries.slice(0, 5).map((entry) => entry.display_name).join(", ");
  return entries.length > 5 ? `${preview} +${entries.length - 5} more` : preview;
}

function liveStatusNote(entry: StandingEntry, standingsCutoff: number | null, index: number) {
  if (standingsCutoff !== null) {
    return index < standingsCutoff ? "Currently qualifies" : "Currently out";
  }
  if (entry.current_status === "ACTIVE" || entry.current_status === "QUALIFIED") {
    return "Currently qualifies";
  }
  if (entry.current_status === "ELIMINATED") {
    return "Currently out";
  }
  return null;
}

function standingsStoryLabel(standingsCutoff: number | null) {
  return standingsCutoff !== null ? "Live qualification view" : "Progression and ranking rules";
}

function formatScoreTotal(value: number) {
  if (Number.isInteger(value)) return `${value}`;
  return value.toFixed(2).replace(/\.00$/, "").replace(/(\.\d)0$/, "$1");
}

interface StandingsTableProps {
  entries: StandingEntry[];
  tournamentStatus?: string;
  advancementKind?: string | null;
  advanceCount?: number | null;
  advancementSummary?: string | null;
  tieBreakRules?: string[];
  leaderboardMetric?: string;
  scoreDirection?: string;
  scoreLabel?: string;
}

export function StandingsTable({
  entries,
  tournamentStatus,
  advancementKind,
  advanceCount,
  advancementSummary,
  tieBreakRules = [],
  leaderboardMetric = "POINTS",
  scoreDirection = "HIGHER_IS_BETTER",
  scoreLabel = "Score",
}: StandingsTableProps) {
  const liveMode = tournamentStatus === "COMPLETED" ? false : hasLiveStandings(entries);
  const showScoreColumn = leaderboardMetric === "SCORE" || entries.some((entry) => entry.score_total !== 0);
  const standingsCutoff = liveMode && advancementKind === "STANDINGS_TOP_N" && advanceCount && advanceCount > 0
    ? Math.min(advanceCount, entries.length)
    : null;
  const showCutLineDetails = standingsCutoff !== null || entries.some((entry) => entry.current_status === "ELIMINATED");
  const qualifyingEntries = standingsCutoff !== null
    ? entries.slice(0, standingsCutoff)
    : entries.filter((entry) => entry.current_status === "ACTIVE" || entry.current_status === "QUALIFIED");
  const outsideEntries = standingsCutoff !== null
    ? entries.slice(standingsCutoff)
    : entries.filter((entry) => entry.current_status === "ELIMINATED");

  if (!entries.length) {
    return (
      <div className="card table-card">
        <div className="card-header-row">
          <h2>Standings</h2>
        </div>
        <p className="muted-text">Standings appear here once results have been recorded.</p>
      </div>
    );
  }

  return (
    <div className="card table-card">
      <div className="card-header-row">
        <div>
          <h2>Standings</h2>
          <p className="muted-text">{liveMode ? "Active entrants show live rank until the final order is locked." : "Final placements are locked in."}</p>
        </div>
      </div>

      {liveMode || tieBreakRules.length || advancementSummary ? (
        <div className="standings-meta-grid">
          {advancementSummary ? (
            <article className="mini-card standings-note-card">
              <span className="eyebrow">{standingsCutoff !== null ? "Cut line" : "Format note"}</span>
              <strong>{standingsCutoff ? `Top ${standingsCutoff} currently advance` : standingsStoryLabel(standingsCutoff)}</strong>
              <p className="muted-text">{advancementSummary}</p>
            </article>
          ) : null}

          {liveMode && showCutLineDetails ? (
            <article className="mini-card standings-note-card">
              <span className="eyebrow">Currently qualifies</span>
              <strong>{qualifyingEntries.length}</strong>
              <p className="muted-text">{nameSummary(qualifyingEntries)}</p>
            </article>
          ) : null}

          {liveMode && showCutLineDetails ? (
            <article className="mini-card standings-note-card">
              <span className="eyebrow">Currently out</span>
              <strong>{outsideEntries.length}</strong>
              <p className="muted-text">{nameSummary(outsideEntries)}</p>
            </article>
          ) : null}

          {tieBreakRules.length ? (
            <article className="mini-card standings-note-card">
              <span className="eyebrow">Tie-break order</span>
              <strong>{tieBreakLabel(tieBreakRules[0])}</strong>
              <p className="muted-text">{tieBreakRules.map((rule) => tieBreakLabel(rule)).join(" -> ")}</p>
            </article>
          ) : null}

          {showScoreColumn ? (
            <article className="mini-card standings-note-card">
              <span className="eyebrow">Leaderboard basis</span>
              <strong>{leaderboardMetricLabel(leaderboardMetric)}</strong>
              <p className="muted-text">{scoreLabel}: {scoreDirectionLabel(scoreDirection)}</p>
            </article>
          ) : null}
        </div>
      ) : null}

      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>{liveMode ? "Rank now" : "Place"}</th>
              <th>Entrant</th>
              <th>Points</th>
              {showScoreColumn ? <th>{scoreLabel}</th> : null}
              <th>Matches</th>
              <th>Best</th>
              <th>Avg.</th>
              <th>Status</th>
            </tr>
          </thead>
          <tbody>
            {entries.map((entry, index) => {
              const liveNote = showCutLineDetails ? liveStatusNote(entry, standingsCutoff, index) : null;
              const rowClassName = [
                standingsCutoff !== null && index < standingsCutoff ? "qualifying-row" : "",
                standingsCutoff !== null && index >= standingsCutoff ? "outside-cut-row" : "",
                standingsCutoff !== null && index === standingsCutoff - 1 ? "cut-line-row" : "",
                standingsCutoff === null && showCutLineDetails && (entry.current_status === "ACTIVE" || entry.current_status === "QUALIFIED") ? "qualifying-row" : "",
                standingsCutoff === null && showCutLineDetails && entry.current_status === "ELIMINATED" ? "outside-cut-row" : "",
              ].filter(Boolean).join(" ");

              return (
                <tr key={entry.participant_id} className={rowClassName}>
                  <td>{standingPositionLabel(entry, index, liveMode)}</td>
                  <td>
                    <strong>{entry.display_name}</strong>
                    {entry.latest_round_name ? <div className="muted-text">Last: {entry.latest_round_name}</div> : null}
                    {liveMode && liveNote ? <div className="table-row-note">{liveNote}</div> : null}
                  </td>
                  <td>{entry.total_points}</td>
                  {showScoreColumn ? <td>{formatScoreTotal(entry.score_total)}</td> : null}
                  <td>{entry.matches_played}</td>
                  <td>{entry.best_rank ?? "-"}</td>
                  <td>{entry.average_rank ?? "-"}</td>
                  <td>
                    <StatusPill value={entry.current_status} />
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
