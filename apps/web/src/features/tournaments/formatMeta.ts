import type { TournamentFormat } from "@podiumforge/shared";

type AdvanceCountMode = "manual" | "hidden" | "fixed-one";

interface TournamentSetupConfig {
  defaultPointsScheme: string;
  fixedHeadToHeadMatchSize: boolean;
  advanceCountMode: AdvanceCountMode;
  pointsOptional: boolean;
  exactParticipantCount?: number;
  minParticipantCount?: number;
  requiresPowerOfTwo?: boolean;
  participantHint?: string;
}

export const tournamentSetupConfig: Record<TournamentFormat, TournamentSetupConfig> = {
  FFA_ELIMINATION: {
    defaultPointsScheme: "1:10, 2:7, 3:5, 4:3, 5:1",
    fixedHeadToHeadMatchSize: false,
    advanceCountMode: "manual",
    pointsOptional: false,
  },
  GROUP_POINTS: {
    defaultPointsScheme: "1:10, 2:7, 3:5, 4:3, 5:1",
    fixedHeadToHeadMatchSize: false,
    advanceCountMode: "manual",
    pointsOptional: false,
  },
  LEADERBOARD_SERIES: {
    defaultPointsScheme: "1:10, 2:7, 3:5, 4:3, 5:1",
    fixedHeadToHeadMatchSize: false,
    advanceCountMode: "hidden",
    pointsOptional: true,
  },
  ROUND_ROBIN: {
    defaultPointsScheme: "1:3, 2:0",
    fixedHeadToHeadMatchSize: true,
    advanceCountMode: "hidden",
    pointsOptional: false,
  },
  SWISS: {
    defaultPointsScheme: "1:3, 2:0",
    fixedHeadToHeadMatchSize: true,
    advanceCountMode: "hidden",
    pointsOptional: false,
  },
  PAGE_PLAYOFF: {
    defaultPointsScheme: "1:3, 2:0",
    fixedHeadToHeadMatchSize: true,
    advanceCountMode: "hidden",
    pointsOptional: true,
    exactParticipantCount: 4,
    participantHint: "Page playoffs currently run as a seeded top-four finals format: seeds 1 and 2 enter the qualifier, while 3 and 4 start in the eliminator.",
  },
  STANDALONE_MATCH: {
    defaultPointsScheme: "1:10, 2:7, 3:5, 4:3, 5:1",
    fixedHeadToHeadMatchSize: false,
    advanceCountMode: "hidden",
    pointsOptional: false,
  },
  BRACKET: {
    defaultPointsScheme: "1:3, 2:0",
    fixedHeadToHeadMatchSize: true,
    advanceCountMode: "fixed-one",
    pointsOptional: true,
  },
  DOUBLE_ELIMINATION: {
    defaultPointsScheme: "1:3, 2:0",
    fixedHeadToHeadMatchSize: true,
    advanceCountMode: "fixed-one",
    pointsOptional: true,
    minParticipantCount: 4,
    requiresPowerOfTwo: true,
    participantHint: "Double-elimination currently supports power-of-two fields such as 4, 8, or 16 entrants.",
  },
};

export function getTournamentSetupConfig(format: TournamentFormat): TournamentSetupConfig {
  return tournamentSetupConfig[format];
}

export function isBracketStyleFormat(format: string | TournamentFormat | undefined) {
  return format === "BRACKET" || format === "DOUBLE_ELIMINATION";
}

export function usesFixedHeadToHeadMatches(format: string | TournamentFormat | undefined) {
  return Boolean(format && tournamentSetupConfig[format as TournamentFormat]?.fixedHeadToHeadMatchSize);
}

export function advanceCountMode(format: string | TournamentFormat | undefined): AdvanceCountMode | null {
  return format ? tournamentSetupConfig[format as TournamentFormat]?.advanceCountMode ?? null : null;
}

export function usesOptionalPointsScheme(format: string | TournamentFormat | undefined) {
  return Boolean(format && tournamentSetupConfig[format as TournamentFormat]?.pointsOptional);
}

export function finalRoundLabel(format: string | undefined, fallback = "Final placement round") {
  switch (format) {
    case "BRACKET":
    case "DOUBLE_ELIMINATION":
      return "Championship round";
    case "ROUND_ROBIN":
      return "Final league round";
    case "LEADERBOARD_SERIES":
      return "Final scheduled round";
    case "SWISS":
      return "Final Swiss round";
    case "PAGE_PLAYOFF":
      return "Grand final";
    default:
      return fallback;
  }
}

export function tieBreakLabel(rule: string | undefined, fallback = "Default order") {
  switch (rule) {
    case "TOTAL_POINTS":
    case "TOTAL_POINTS_DESC":
      return "Most total points";
    case "SCORE_TOTAL":
      return "Best score total";
    case "BEST_RANK_ASC":
      return "Best single finish";
    case "AVERAGE_RANK_ASC":
      return "Best average finish";
    case "DISPLAY_NAME_ASC":
      return "Alphabetical order";
    case undefined:
      return fallback;
    default:
      return rule;
  }
}

export function activeFieldHeading(format: string | undefined) {
  switch (format) {
    case "BRACKET":
      return "Still alive in bracket";
    case "DOUBLE_ELIMINATION":
      return "Still alive across both brackets";
    case "GROUP_POINTS":
      return "Still in contention";
    case "LEADERBOARD_SERIES":
      return "Full leaderboard field";
    case "ROUND_ROBIN":
      return "League field";
    case "SWISS":
      return "Swiss field";
    case "PAGE_PLAYOFF":
      return "Still alive in playoff";
    case "STANDALONE_MATCH":
      return "Current field";
    default:
      return "Still alive";
  }
}

export function dashboardSubtitle(format: string | undefined) {
  switch (format) {
    case "BRACKET":
      return "Bracket path, live match slate, and podium updates.";
    case "DOUBLE_ELIMINATION":
      return "Upper bracket, lower bracket, and grand-final pressure in one live view.";
    case "GROUP_POINTS":
      return "Leaderboard movement, active tables, and qualification watch.";
    case "LEADERBOARD_SERIES":
      return "Running leaderboard totals, active groups, and every round still in play.";
    case "ROUND_ROBIN":
      return "League table movement, current fixtures, and title-race updates.";
    case "SWISS":
      return "Score-group pairings, leaderboard pressure, and late-round separation.";
    case "PAGE_PLAYOFF":
      return "Qualifier pressure, second-chance drama, and a direct path into the grand final.";
    case "STANDALONE_MATCH":
      return "Feature match standings and final podium updates.";
    default:
      return "Live standings, current round, and podium updates.";
  }
}

export function tournamentPulse(format: string | undefined, status: string | undefined) {
  if (status === "COMPLETED") {
    return "The event is complete and the final order is locked in.";
  }
  switch (format) {
    case "BRACKET":
      return "Follow the live side of the bracket and watch the path toward the final tighten up.";
    case "DOUBLE_ELIMINATION":
      return "Watch contenders fall into the lower bracket, fight back, and try to reach the grand final from the long road.";
    case "GROUP_POINTS":
      return "Points from every table feed the live leaderboard, so every result can move the cut line.";
    case "LEADERBOARD_SERIES":
      return "Every scheduled round feeds the same leaderboard, so the final order keeps moving until the last result lands.";
    case "ROUND_ROBIN":
      return "Every round updates one shared league table, so the title race stays visible from the first fixture to the last.";
    case "SWISS":
      return "Each new pairing reacts to the current table, so every result reshapes who meets next and who can still top the standings.";
    case "PAGE_PLAYOFF":
      return "The qualifier winner waits in the grand final while the rest of the top four fight through the second-chance path.";
    case "STANDALONE_MATCH":
      return "One table decides the full ranking, so the board becomes the final result as soon as scores land.";
    default:
      return "Heats drive the cut line round by round, so each table decides who stays alive and who drops out.";
  }
}

export function advancementSummary(summary: string | null | undefined, fallback = "No advancement rule configured.") {
  return summary ?? fallback;
}

export function participantRuleHint(format: TournamentFormat) {
  return tournamentSetupConfig[format].participantHint ?? null;
}

export function participantCountValidationError(format: TournamentFormat, participantCount: number) {
  const config = tournamentSetupConfig[format];

  if (config.exactParticipantCount && participantCount !== config.exactParticipantCount) {
    return `${getTournamentFormatName(format)} requires exactly ${config.exactParticipantCount} participants.`;
  }

  if (config.minParticipantCount && participantCount < config.minParticipantCount) {
    return `${getTournamentFormatName(format)} requires at least ${config.minParticipantCount} participants.`;
  }

  if (config.requiresPowerOfTwo && participantCount > 0 && (participantCount & (participantCount - 1)) !== 0) {
    return `${getTournamentFormatName(format)} currently requires 4, 8, 16, or another power-of-two participant count.`;
  }

  return null;
}

export function advanceCountHint(format: TournamentFormat) {
  switch (format) {
    case "STANDALONE_MATCH":
      return "A standalone match ends immediately, so no one advances to another round.";
    case "ROUND_ROBIN":
      return "Round-robin play runs through the full schedule, so the table decides the champion without per-round advancement.";
    case "SWISS":
      return "Swiss play runs for a fixed number of rounds, so the final table decides the champion without manual advancement targets.";
    case "PAGE_PLAYOFF":
      return "Page playoffs always run qualifier, eliminator, preliminary final, and grand final logic from a seeded top four.";
    case "BRACKET":
      return "Bracket matches always send exactly one winner forward.";
    case "DOUBLE_ELIMINATION":
      return "Winners stay in the upper bracket, while first-time losers move into the lower bracket.";
    case "GROUP_POINTS":
      return "This is how many entrants survive based on the shared leaderboard.";
    case "LEADERBOARD_SERIES":
      return "A leaderboard series keeps the full field active for a fixed number of scheduled rounds.";
    default:
      return "This is how many finishers survive from each individual match.";
  }
}

export function scoreDirectionLabel(value: string | undefined, fallback = "Higher is better") {
  switch (value) {
    case "LOWER_IS_BETTER":
      return "Lower is better";
    case "HIGHER_IS_BETTER":
      return "Higher is better";
    default:
      return fallback;
  }
}

export function leaderboardMetricLabel(value: string | undefined, fallback = "Points") {
  switch (value) {
    case "SCORE":
      return "Score";
    case "POINTS":
      return "Points";
    default:
      return fallback;
  }
}

function getTournamentFormatName(format: TournamentFormat) {
  return format
    .replace(/_/g, " ")
    .toLowerCase()
    .replace(/^[a-z]/, (character) => character.toUpperCase());
}
