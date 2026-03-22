import type { CSSProperties } from "react";
import { Link } from "react-router-dom";
import type { MatchEntrant, MatchRecord, RoundRecord } from "../api/types";
import { nextPowerOfTwo } from "../features/tournaments/formatGuides";
import { StatusPill } from "./StatusPill";

interface BracketBoardProps {
  rounds: RoundRecord[];
  participantCount?: number;
  title?: string;
  eyebrow?: string;
  subtitle?: string;
  showFutureRounds?: boolean;
  matchHrefBuilder?: (match: MatchRecord) => string | null;
}

interface DisplayEntrant {
  key: string;
  displayName: string;
  secondaryLabel: string;
  rankLabel: string;
  isWinner: boolean;
  isPlaceholder: boolean;
}

interface DisplayMatch {
  key: string;
  name: string;
  status: string;
  isBye: boolean;
  isPlaceholder: boolean;
  href: string | null;
  entrants: DisplayEntrant[];
}

interface DisplayRound {
  key: string;
  name: string;
  number: number;
  status: string;
  isPlaceholder: boolean;
  isFinal: boolean;
  matches: DisplayMatch[];
}

function roundNameFromSize(matchCount: number, roundIndex: number, totalRounds: number) {
  if (roundIndex === totalRounds - 1) return "Final";
  if (roundIndex === totalRounds - 2) return "Semifinal";
  if (roundIndex === totalRounds - 3) return "Quarterfinal";
  return `Round of ${matchCount * 2}`;
}

function secondaryLabelForEntrant(entrant: MatchEntrant) {
  if (entrant.seed_number) return "Bracket seed";
  if (entrant.score !== null) return `Score ${entrant.score}`;
  return `Slot ${entrant.slot_number}`;
}

function toDisplayEntrants(match: MatchRecord): DisplayEntrant[] {
  return match.entrants
    .slice()
    .sort((left, right) => left.slot_number - right.slot_number)
    .map((entrant) => ({
      key: entrant.participant_id,
      displayName: entrant.display_name,
      secondaryLabel: secondaryLabelForEntrant(entrant),
      rankLabel: entrant.rank ? `#${entrant.rank}` : entrant.seed_number ? `S${entrant.seed_number}` : "-",
      isWinner: entrant.rank === 1,
      isPlaceholder: false,
    }));
}


function toDisplayMatch(
  match: MatchRecord,
  matchHrefBuilder?: (match: MatchRecord) => string | null,
): DisplayMatch {
  return {
    key: match.id,
    name: match.name,
    status: match.status,
    isBye: match.is_bye,
    isPlaceholder: false,
    href: matchHrefBuilder ? matchHrefBuilder(match) : null,
    entrants: toDisplayEntrants(match),
  };
}

function placeholderEntrants(roundIndex: number, matchIndex: number): DisplayEntrant[] {
  if (roundIndex === 0) {
    return [
      {
        key: `opening-${matchIndex}-1`,
        displayName: "Pending entrant",
        secondaryLabel: "Slot to be assigned",
        rankLabel: "-",
        isWinner: false,
        isPlaceholder: true,
      },
      {
        key: `opening-${matchIndex}-2`,
        displayName: "Pending entrant",
        secondaryLabel: "Slot to be assigned",
        rankLabel: "-",
        isWinner: false,
        isPlaceholder: true,
      },
    ];
  }

  const sourceA = matchIndex * 2 + 1;
  const sourceB = sourceA + 1;
  return [
    {
      key: `pending-${roundIndex}-${matchIndex}-1`,
      displayName: `Winner ${sourceA}`,
      secondaryLabel: "Previous matchup",
      rankLabel: "-",
      isWinner: false,
      isPlaceholder: true,
    },
    {
      key: `pending-${roundIndex}-${matchIndex}-2`,
      displayName: `Winner ${sourceB}`,
      secondaryLabel: "Previous matchup",
      rankLabel: "-",
      isWinner: false,
      isPlaceholder: true,
    },
  ];
}

function displayRounds(
  rounds: RoundRecord[],
  participantCount?: number,
  showFutureRounds = true,
  matchHrefBuilder?: (match: MatchRecord) => string | null,
): DisplayRound[] {
  const orderedRounds = rounds.slice().sort((left, right) => left.number - right.number);
  const minimumParticipantCount = Math.max(participantCount ?? 0, 2);
  const fieldSize = participantCount ? nextPowerOfTwo(minimumParticipantCount) : Math.max((orderedRounds[0]?.matches.length ?? 1) * 2, 2);
  const totalRounds = showFutureRounds ? Math.max(orderedRounds.length, Math.log2(fieldSize)) : orderedRounds.length;

  return Array.from({ length: totalRounds }, (_, roundIndex) => {
    const expectedMatchCount = Math.max(1, fieldSize / 2 ** (roundIndex + 1));
    const round = orderedRounds[roundIndex];
    const matches = Array.from({ length: expectedMatchCount }, (_, matchIndex) => {
      const match = round?.matches.slice().sort((left, right) => left.sequence - right.sequence)[matchIndex];
      if (match) {
        return toDisplayMatch(match, matchHrefBuilder);
      }

      return {
        key: `placeholder-round-${roundIndex + 1}-match-${matchIndex + 1}`,
        name: `${roundNameFromSize(expectedMatchCount, roundIndex, totalRounds)} ${matchIndex + 1}`,
        status: "PENDING",
        isBye: false,
        isPlaceholder: true,
        href: null,
        entrants: placeholderEntrants(roundIndex, matchIndex),
      } satisfies DisplayMatch;
    });

    return {
      key: round?.id ?? `display-round-${roundIndex + 1}`,
      name: round?.name ?? roundNameFromSize(expectedMatchCount, roundIndex, totalRounds),
      number: round?.number ?? roundIndex + 1,
      status: round?.status ?? "PENDING",
      isPlaceholder: !round,
      isFinal: roundIndex === totalRounds - 1,
      matches,
    } satisfies DisplayRound;
  });
}

export function BracketBoard({
  rounds,
  participantCount,
  title = "Bracket view",
  eyebrow = "Bracket path",
  subtitle = "Classic left-to-right elimination view with played matches, auto-byes, and future rounds mapped out in advance.",
  showFutureRounds = true,
  matchHrefBuilder,
}: BracketBoardProps) {
  const roundsForDisplay = displayRounds(rounds, participantCount, showFutureRounds, matchHrefBuilder);

  return (
    <section className="card bracket-board-card">
      <div className="card-header-row">
        <div>
          <span className="eyebrow">{eyebrow}</span>
          <h2>{title}</h2>
          <p className="muted-text">{subtitle}</p>
        </div>
      </div>

      <div className="bracket-scroll">
        <div className="bracket-columns">
          {roundsForDisplay.map((round, index) => (
            <section
              key={round.key}
              className={`bracket-round-column ${round.isFinal ? "final-round-column" : ""}`}
              style={{ "--round-depth": `${index}`, "--round-match-count": `${round.matches.length}` } as CSSProperties}
            >
              <header className="bracket-round-header">
                <span className="eyebrow">Round {round.number}</span>
                <h3>{round.name}</h3>
                {round.isPlaceholder ? <span className="bracket-future-pill">Upcoming</span> : <StatusPill value={round.status} />}
              </header>

              <div className="bracket-match-stack">
                {round.matches.map((match) => {
                  const cardClassName = `bracket-match-card ${match.isPlaceholder ? "placeholder-match-card" : ""} ${match.isBye ? "bye-match-card" : ""} ${match.href ? "bracket-match-link-card" : ""}`;
                  const content = (
                    <>
                      <div className="bracket-match-header">
                        <div>
                          <strong>{match.name}</strong>
                          <div className="muted-text">
                            {match.isPlaceholder
                              ? "Waiting for previous winners"
                              : match.isBye
                                ? "Automatic advance"
                                : `${match.entrants.length} entrants`}
                          </div>
                        </div>
                        {!match.isPlaceholder ? <StatusPill value={match.status} /> : null}
                      </div>

                      <div className="bracket-entrant-stack">
                        {match.entrants.map((entrant) => (
                          <div
                            key={entrant.key}
                            className={`bracket-entrant-row ${entrant.isWinner ? "winner-row" : ""} ${entrant.isPlaceholder ? "placeholder-entrant-row" : ""}`}
                          >
                            <div>
                              <strong>{entrant.displayName}</strong>
                              <div className="muted-text">{entrant.secondaryLabel}</div>
                            </div>
                            <div className="bracket-rank-pill">{entrant.rankLabel}</div>
                          </div>
                        ))}
                      </div>
                    </>
                  );

                  return match.href ? (
                    <Link key={match.key} to={match.href} className={cardClassName} aria-label={`Open ${match.name}`}>
                      {content}
                    </Link>
                  ) : (
                    <article key={match.key} className={cardClassName}>
                      {content}
                    </article>
                  );
                })}
              </div>
            </section>
          ))}
        </div>
      </div>
    </section>
  );
}
