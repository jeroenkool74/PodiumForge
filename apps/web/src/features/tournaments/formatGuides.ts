import { placementLabel, tournamentFormatLabels, type TournamentFormat } from "@podiumforge/shared";
import type { PlacementPoint } from "../../api/types";

export interface FormatGuide {
  label: string;
  tagline: string;
  description: string;
  bestFor: string;
  steps: string[];
  scoringHint: string;
  preview: Array<{ label: string; slots: string[] }>;
}

export const tournamentFormatOrder: TournamentFormat[] = [
  "FFA_ELIMINATION",
  "GROUP_POINTS",
  "LEADERBOARD_SERIES",
  "ROUND_ROBIN",
  "SWISS",
  "PAGE_PLAYOFF",
  "STANDALONE_MATCH",
  "DOUBLE_ELIMINATION",
  "BRACKET",
];

export const tournamentFormatGuides: Record<TournamentFormat, FormatGuide> = {
  FFA_ELIMINATION: {
    label: tournamentFormatLabels.FFA_ELIMINATION,
    tagline: "Several heats, then a cleaner final round.",
    description: "Players are split into free-for-all matches. The top finishers from each match survive and everyone else gets classified right away.",
    bestFor: "LAN nights, battle royale heats, and any event where each match should cut the field down quickly.",
    steps: [
      "Split entrants into ranked heats.",
      "Advance the best finishers from every heat.",
      "Run another round until one final match decides the top places.",
    ],
    scoringHint: "Points can reward every placement, but advancement is driven by placement inside each individual match.",
    preview: [
      { label: "Heats", slots: ["Heat A", "Heat B", "Heat C"] },
      { label: "Cut", slots: ["Top finishers advance"] },
      { label: "Final", slots: ["Champion match"] },
    ],
  },
  GROUP_POINTS: {
    label: "Group leaderboard format",
    tagline: "Everyone chases one running leaderboard.",
    description: "Entrants still play in groups, but qualification is based on total points across the round instead of finishing top N inside one specific match.",
    bestFor: "Leagues, Swiss-like multiplayer events, or formats where consistency across multiple tables should matter most.",
    steps: [
      "Run ranked group matches for the full field.",
      "Add points from every table into one standings list.",
      "Advance the top overall performers to the next round.",
    ],
    scoringHint: "The points scheme is the heart of this format because the global leaderboard decides who moves on.",
    preview: [
      { label: "Groups", slots: ["Match A", "Match B", "Match C"] },
      { label: "Leaderboard", slots: ["Total points ranking"] },
      { label: "Advance", slots: ["Top overall continue"] },
    ],
  },
  LEADERBOARD_SERIES: {
    label: tournamentFormatLabels.LEADERBOARD_SERIES,
    tagline: "Fixed rounds, one running leaderboard.",
    description: "The full field stays alive for a scheduled number of grouped rounds while one cumulative leaderboard decides the champion at the end.",
    bestFor: "Repeated races, map rotations, heats, and any event where several rounds should roll into one final table without eliminations.",
    steps: [
      "Seed entrants into the opening groups.",
      "Run the configured number of rounds with the same full field still active.",
      "Lock the final order from the cumulative leaderboard after the last scheduled round.",
    ],
    scoringHint: "Choose whether the running leaderboard should follow total points or total score, then use the score direction to decide whether higher or lower values are better.",
    preview: [
      { label: "Round 1", slots: ["Opening groups"] },
      { label: "Running table", slots: ["Cumulative leaderboard"] },
      { label: "Finish", slots: ["Champion by totals"] },
    ],
  },
  ROUND_ROBIN: {
    label: tournamentFormatLabels.ROUND_ROBIN,
    tagline: "League table first, champion last.",
    description: "Every entrant faces every other entrant once in a full season schedule. The standings table becomes the main story from opening round to final whistle.",
    bestFor: "Club leagues, season play, and smaller fields where fairness across the whole schedule matters more than quick elimination.",
    steps: [
      "Generate a full head-to-head schedule across all entrants.",
      "Award points after each league match and update the table live.",
      "Lock the final placements when the last scheduled round is complete.",
    ],
    scoringHint: "Points decide the table here, so use a win/loss scheme that fits your sport and let tie-break rules separate equal records.",
    preview: [
      { label: "Schedule", slots: ["Everyone plays everyone"] },
      { label: "Table", slots: ["Live league standings"] },
      { label: "Final order", slots: ["Champion by points"] },
    ],
  },
  SWISS: {
    label: tournamentFormatLabels.SWISS,
    tagline: "Fixed rounds, pair by current score.",
    description: "Everyone stays in the event for a set number of rounds while pairings tighten around similar records. The standings table decides the champion at the end.",
    bestFor: "Chess-style events, card games, board games, and larger fields that need fewer rounds than a full league schedule.",
    steps: [
      "Start with seeded opening pairings.",
      "Re-pair each round using the live standings so similar records meet.",
      "Lock the table after the final scheduled Swiss round.",
    ],
    scoringHint: "Use a simple win/loss points scheme because the running table drives every later pairing and the final ranking.",
    preview: [
      { label: "Opening", slots: ["Seeded pairings"] },
      { label: "Middle rounds", slots: ["Score-based pairings"] },
      { label: "Final table", slots: ["Champion by points"] },
    ],
  },
  PAGE_PLAYOFF: {
    label: tournamentFormatLabels.PAGE_PLAYOFF,
    tagline: "Top four finals with a double chance for seeds 1 and 2.",
    description: "The top seeds start in the qualifier, the lower seeds start in the eliminator, and the qualifier winner earns a direct path to the grand final.",
    bestFor: "League or Swiss finals nights, seeded top-four playoffs, and events that want to reward the highest regular-season finishers.",
    steps: [
      "Seed 1 and 2 meet in the qualifier while 3 and 4 start in the eliminator.",
      "The qualifier loser meets the eliminator winner in the preliminary final.",
      "The qualifier winner waits in the grand final for the preliminary-final survivor.",
    ],
    scoringHint: "Winning the right match matters more than the raw points total here; use points mainly for dashboards and clean tie-break summaries.",
    preview: [
      { label: "Opening", slots: ["1 vs 2 qualifier", "3 vs 4 eliminator"] },
      { label: "Second chance", slots: ["Qualifier loser vs eliminator winner"] },
      { label: "Final", slots: ["Qualifier winner vs survivor"] },
    ],
  },
  STANDALONE_MATCH: {
    label: tournamentFormatLabels.STANDALONE_MATCH,
    tagline: "One match, one final ranking.",
    description: "All entrants play a single ranked match and the result immediately locks the full finishing order.",
    bestFor: "Showmatches, finals tables, small pods, or any one-off event that should finish in a single game.",
    steps: [
      "Seat everyone in one ranked match.",
      "Enter the final order once the match ends.",
      "Publish the podium and placements instantly.",
    ],
    scoringHint: "Points are optional flavor here; the main outcome is the final ranking from that one match.",
    preview: [
      { label: "Feature match", slots: ["Single ranked table"] },
      { label: "Result", slots: ["1st to last locked"] },
    ],
  },
  BRACKET: {
    label: tournamentFormatLabels.BRACKET,
    tagline: "Classic knockout with seeded head-to-head matches.",
    description: "Entrants are seeded into a single-elimination bracket. Winners move forward, losers are out, and top seeds can receive automatic byes when the bracket is not full.",
    bestFor: "Traditional esports playoffs, cup tournaments, and any event that should feel like a familiar bracket on screen.",
    steps: [
      "Seed entrants into a head-to-head bracket.",
      "Auto-place byes when the bracket needs empty slots.",
      "Advance winners until the final decides the champion.",
    ],
    scoringHint: "Winning each match is what matters most; points mainly help secondary table summaries.",
    preview: [
      { label: "Bracket", slots: ["1 vs 8", "4 vs 5", "2 vs 7", "3 vs 6"] },
      { label: "Semis", slots: ["Winner", "Winner"] },
      { label: "Final", slots: ["Champion"] },
    ],
  },
  DOUBLE_ELIMINATION: {
    label: tournamentFormatLabels.DOUBLE_ELIMINATION,
    tagline: "Everyone gets one loss before elimination.",
    description: "Entrants start in the winners bracket, drop to the losers bracket after their first defeat, and are only knocked out after a second loss.",
    bestFor: "Fighting game brackets, longer playoffs, and events that want a comeback path without going full round-robin.",
    steps: [
      "Seed the field into the winners bracket.",
      "Send first-time losers into the lower bracket.",
      "Finish with a grand final between the upper-bracket and lower-bracket survivors.",
    ],
    scoringHint: "Winning matches remains the main story; points are optional support for dashboards and side summaries.",
    preview: [
      { label: "Winners", slots: ["Upper path", "Stay alive"] },
      { label: "Losers", slots: ["Second chance", "Fight back"] },
      { label: "Final", slots: ["Grand final"] },
    ],
  },
};

export function getTournamentFormatGuide(format: string): FormatGuide {
  if (format in tournamentFormatGuides) {
    return tournamentFormatGuides[format as TournamentFormat];
  }
  return tournamentFormatGuides.FFA_ELIMINATION;
}

export function sortPointsScheme(pointsScheme: PlacementPoint[] = []): PlacementPoint[] {
  return [...pointsScheme].sort((left, right) => left.placement - right.placement);
}

export function nextPowerOfTwo(value: number): number {
  let power = 1;
  while (power < value) {
    power *= 2;
  }
  return power;
}

export function estimateRoundCount(
  format: string,
  participantCount: number,
  matchSize: number,
  advanceCount: number | null | undefined,
  roundCount?: number | null,
): number {
  if (participantCount <= 1) return 0;
  if (format === "STANDALONE_MATCH") return 1;
  if (format === "LEADERBOARD_SERIES") return Math.max(1, roundCount ?? 1);
  if (format === "ROUND_ROBIN") {
    if (participantCount <= 1) return 0;
    return participantCount % 2 === 0 ? participantCount - 1 : participantCount;
  }
  if (format === "SWISS") {
    return Math.max(1, Math.ceil(Math.log2(Math.max(2, participantCount))));
  }
  if (format === "PAGE_PLAYOFF") {
    return 3;
  }
  if (format === "BRACKET") {
    return Math.log2(nextPowerOfTwo(Math.max(2, participantCount)));
  }
  if (format === "DOUBLE_ELIMINATION") {
    return Math.log2(nextPowerOfTwo(Math.max(4, participantCount))) * 2 + 1;
  }

  if (!advanceCount || participantCount <= matchSize) {
    return 1;
  }

  let rounds = 1;
  let current = participantCount;
  while (current > matchSize) {
    current = Math.ceil(current / matchSize) * advanceCount;
    rounds += 1;
  }
  return rounds;
}

export function pointsSchemeInputToList(input: string): PlacementPoint[] {
  return input
    .split(",")
    .map((part) => part.trim())
    .filter(Boolean)
    .map((part) => {
      const [placement, points] = part.split(":").map((value) => Number(value.trim()));
      return { placement, points };
    })
    .filter((item) => Number.isFinite(item.placement) && Number.isFinite(item.points) && item.placement > 0 && item.points >= 0);
}

export function placementPreviewLabel(placement: number) {
  return placementLabel(placement);
}
