import { estimateRoundCount, getTournamentFormatGuide, nextPowerOfTwo, placementPreviewLabel, sortPointsScheme } from "../features/tournaments/formatGuides";
import type { PlacementPoint } from "../api/types";
import { usesFixedHeadToHeadMatches } from "../features/tournaments/formatMeta";

interface TournamentFormatInsightProps {
  format: string;
  participantCount: number;
  matchSize: number | null;
  advanceCount: number | null;
  pointsScheme?: PlacementPoint[];
  heading?: string;
}

function advanceSummary(format: string, advanceCount: number | null) {
  if (format === "STANDALONE_MATCH") return "No next round needed";
  if (format === "ROUND_ROBIN") return "Full schedule decides the table";
  if (format === "SWISS") return "Fixed score-based pairings";
  if (format === "PAGE_PLAYOFF") return "Seeds 1 and 2 get a second chance";
  if (format === "BRACKET") return "One winner per match";
  if (format === "DOUBLE_ELIMINATION") return "Two losses to be eliminated";
  if (!advanceCount) return "Manual progression";
  return format === "GROUP_POINTS" ? `Top ${advanceCount} overall advance` : `Top ${advanceCount} per match advance`;
}

function structureSummary(
  format: string,
  participantCount: number,
  matchSize: number | null,
  advanceCount: number | null,
) {
  if (!participantCount) {
    return "Add entrants to preview how this setup will unfold in round one.";
  }

  if (format === "STANDALONE_MATCH") {
    return `${participantCount} entrants go straight into one ranked match and finish with a full final order.`;
  }

  if (format === "ROUND_ROBIN") {
    const rounds = participantCount % 2 === 0 ? participantCount - 1 : participantCount;
    const matchesPerRound = Math.floor(participantCount / 2);
    return `${participantCount} entrants create a ${rounds}-round league schedule with about ${matchesPerRound} simultaneous matches each round.`;
  }

  if (format === "SWISS") {
    const rounds = Math.max(1, Math.ceil(Math.log2(Math.max(2, participantCount))));
    return `${participantCount} entrants play ${rounds} Swiss ${rounds === 1 ? "round" : "rounds"}, with pairings tightening around current records each time.`;
  }

  if (format === "PAGE_PLAYOFF") {
    return `${participantCount} entrants fill a fixed three-match finals path where the qualifier winner waits in the grand final and the qualifier loser gets one more life.`;
  }

  if (format === "BRACKET") {
    const fieldSize = nextPowerOfTwo(Math.max(2, participantCount));
    const byes = fieldSize - participantCount;
    return byes
      ? `${participantCount} entrants fill a ${fieldSize}-slot bracket, so ${byes} top seeds receive automatic byes into the next step.`
      : `${participantCount} entrants fill a clean ${fieldSize}-slot bracket with no byes needed.`;
  }

  if (format === "DOUBLE_ELIMINATION") {
    return `${participantCount} entrants start in the winners bracket and only leave the tournament after a second loss.`;
  }

  const actualMatchSize = Math.max(2, matchSize ?? 2);
  const openingMatches = Math.ceil(participantCount / actualMatchSize);
  const nextField = advanceCount ? openingMatches * advanceCount : null;

  if (!advanceCount || participantCount <= actualMatchSize) {
    return `${participantCount} entrants fit into ${openingMatches} opening ${openingMatches === 1 ? "match" : "matches"}.`;
  }

  return `${participantCount} entrants create ${openingMatches} opening ${openingMatches === 1 ? "match" : "matches"}; the next round would start with about ${nextField} survivors.`;
}

export function TournamentFormatInsight({
  format,
  participantCount,
  matchSize,
  advanceCount,
  pointsScheme = [],
  heading = "Format guide",
}: TournamentFormatInsightProps) {
  const guide = getTournamentFormatGuide(format);
  const sortedPoints = sortPointsScheme(pointsScheme);
  const roundEstimate = estimateRoundCount(format, participantCount, matchSize ?? 2, advanceCount);
  const setupSummary = structureSummary(format, participantCount, matchSize, advanceCount);

  return (
    <section className="card format-insight-card">
      <div className="card-header-row">
        <div>
          <span className="eyebrow">{heading}</span>
          <h2>{guide.label}</h2>
          <p className="muted-text">{guide.tagline}</p>
        </div>
      </div>

      <div className="format-insight-grid">
        <div className="content-stack">
          <p>{guide.description}</p>
          <div className="format-metric-grid">
            <div className="mini-card format-metric-card">
              <strong>Entrants</strong>
              <span>{participantCount || "-"}</span>
            </div>
            <div className="mini-card format-metric-card">
              <strong>Match size</strong>
              <span>{usesFixedHeadToHeadMatches(format) ? 2 : matchSize ?? "-"}</span>
            </div>
            <div className="mini-card format-metric-card">
              <strong>Advancement</strong>
              <span>{advanceSummary(format, advanceCount)}</span>
            </div>
            <div className="mini-card format-metric-card">
              <strong>Expected rounds</strong>
              <span>{roundEstimate || "-"}</span>
            </div>
          </div>

          <div className="content-stack">
            <h3>How it plays</h3>
            <ul className="feature-list">
              {guide.steps.map((step) => (
                <li key={step}>{step}</li>
              ))}
            </ul>
          </div>

          <div className="mini-card note-card">
            <strong>Best for</strong>
            <p>{guide.bestFor}</p>
          </div>

          <div className="mini-card note-card">
            <strong>What this setup creates</strong>
            <p>{setupSummary}</p>
          </div>
        </div>

        <div className="content-stack">
          <div className="scheme-preview-grid">
            {guide.preview.map((column) => (
              <div key={column.label} className="scheme-preview-column">
                <span className="eyebrow">{column.label}</span>
                <div className="scheme-preview-stack">
                  {column.slots.map((slot) => (
                    <div key={slot} className="scheme-preview-slot">
                      {slot}
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>

          <div className="mini-card note-card">
            <strong>Points at a glance</strong>
            {sortedPoints.length ? (
              <div className="points-preview-row">
                {sortedPoints.slice(0, 6).map((item) => (
                  <div key={`${item.placement}-${item.points}`} className="points-preview-pill">
                    <span>{placementPreviewLabel(item.placement)}</span>
                    <strong>{item.points} pts</strong>
                  </div>
                ))}
              </div>
            ) : null}
            <p>{guide.scoringHint}</p>
          </div>
        </div>
      </div>
    </section>
  );
}
