import type { MatchRecord, RoundRecord } from "../api/types";
import { BracketBoard } from "./BracketBoard";

interface DoubleEliminationBoardProps {
  rounds: RoundRecord[];
  participantCount: number;
  title?: string;
  matchHrefBuilder?: (match: MatchRecord) => string | null;
}

export function DoubleEliminationBoard({
  rounds,
  participantCount,
  title = "Double-elimination bracket",
  matchHrefBuilder,
}: DoubleEliminationBoardProps) {
  const winnersRounds = rounds.filter((round) => round.bracket_kind === "WINNERS");
  const losersRounds = rounds.filter((round) => round.bracket_kind === "LOSERS");
  const finalRounds = rounds.filter((round) => round.bracket_kind?.startsWith("GRAND_FINAL"));

  return (
    <section className="content-stack">
      <div className="card-header-row">
        <div>
          <span className="eyebrow">Dual bracket</span>
          <h2>{title}</h2>
          <p className="muted-text">Winners stay on the upper path, while one loss drops a contender into the lower bracket for a last-chance run.</p>
        </div>
      </div>

      <div className="double-bracket-grid">
        <BracketBoard
          rounds={winnersRounds}
          participantCount={participantCount}
          title="Winners bracket"
          eyebrow="Upper bracket"
          subtitle="Unbeaten contenders stay here until the upper-bracket finalist locks in a grand-final seat."
          matchHrefBuilder={matchHrefBuilder}
        />

        <BracketBoard
          rounds={losersRounds}
          title="Losers bracket"
          eyebrow="Lower bracket"
          subtitle="One loss sends contenders here, where every remaining match becomes survive-or-go-home."
          showFutureRounds={false}
          matchHrefBuilder={matchHrefBuilder}
        />
      </div>

      {finalRounds.length ? (
        <BracketBoard
          rounds={finalRounds}
          title="Grand final"
          eyebrow="Championship"
          subtitle="The winners-bracket survivor meets the lower-bracket survivor for the last series on the board."
          showFutureRounds={false}
          matchHrefBuilder={matchHrefBuilder}
        />
      ) : null}
    </section>
  );
}
