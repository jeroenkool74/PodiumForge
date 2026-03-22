import { placementLabel } from "@podiumforge/shared";
import type { StandingEntry } from "../api/types";
import { activeFieldHeading } from "../features/tournaments/formatMeta";
import { podiumEntries } from "../features/tournaments/standingPresentation";

interface TournamentHighlightsProps {
  format: string;
  status: string;
  standings: StandingEntry[];
  activeNames: string[];
  eliminatedNames: string[];
}

export function TournamentHighlights({
  format,
  status,
  standings,
  activeNames,
  eliminatedNames,
}: TournamentHighlightsProps) {
  const podium = podiumEntries(standings);
  const champion = podium.find((entry) => entry.final_placement === 1) ?? standings[0] ?? null;

  if (status === "COMPLETED") {
    return (
      <div className="chip-grid">
        <div className="chip-panel success-panel">
          <h3>Champion</h3>
          <p>{champion ? champion.display_name : "Final result pending."}</p>
        </div>
        <div className="chip-panel">
          <h3>Podium</h3>
          <p>
            {podium.length
              ? podium.map((entry) => `${placementLabel(entry.final_placement)} ${entry.display_name}`).join("  |  ")
              : "The standings table below carries the full final classification."}
          </p>
        </div>
      </div>
    );
  }

  return (
      <div className="chip-grid">
        <div className="chip-panel success-panel">
          <h3>{activeFieldHeading(format)}</h3>
          <p>{activeNames.length ? activeNames.join(", ") : "Nobody is active yet."}</p>
        </div>
      <div className="chip-panel danger-panel">
        <h3>Classified out</h3>
        <p>{eliminatedNames.length ? eliminatedNames.join(", ") : "Nobody has been knocked out yet."}</p>
      </div>
    </div>
  );
}
