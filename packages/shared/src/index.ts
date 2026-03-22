export type RoleName = "ADMIN" | "TOURNAMENT_EDITOR";
export type TournamentFormat = "FFA_ELIMINATION" | "GROUP_POINTS" | "ROUND_ROBIN" | "SWISS" | "PAGE_PLAYOFF" | "STANDALONE_MATCH" | "BRACKET" | "DOUBLE_ELIMINATION";
export type ParticipantType = "PLAYER" | "TEAM";

export const tournamentFormatLabels: Record<TournamentFormat, string> = {
  FFA_ELIMINATION: "Free-for-all elimination",
  GROUP_POINTS: "Group points format",
  ROUND_ROBIN: "Round-robin league",
  SWISS: "Swiss system",
  PAGE_PLAYOFF: "Page playoff",
  STANDALONE_MATCH: "Standalone ranked match",
  BRACKET: "Single-elimination bracket",
  DOUBLE_ELIMINATION: "Double-elimination bracket",
};

export const participantTypeLabels: Record<ParticipantType, string> = {
  PLAYER: "Players",
  TEAM: "Teams",
};

export const statusLabels: Record<string, string> = {
  DRAFT: "Draft",
  LIVE: "Live",
  COMPLETED: "Completed",
  ACTIVE: "Active",
  QUALIFIED: "Qualified",
  ELIMINATED: "Eliminated",
  FINALIZED: "Finalized",
  SCHEDULED: "Scheduled",
  CANCELED: "Canceled",
};

export function getTournamentFormatLabel(value: string): string {
  return tournamentFormatLabels[value as TournamentFormat] ?? value;
}

export function getParticipantTypeLabel(value: string): string {
  return participantTypeLabels[value as ParticipantType] ?? value;
}

export function getStatusLabel(value: string): string {
  return statusLabels[value] ?? value;
}

export function placementLabel(value: number | null | undefined): string {
  if (!value) return "-";
  const mod100 = value % 100;
  if (mod100 >= 11 && mod100 <= 13) return `${value}th`;
  const mod10 = value % 10;
  if (mod10 === 1) return `${value}st`;
  if (mod10 === 2) return `${value}nd`;
  if (mod10 === 3) return `${value}rd`;
  return `${value}th`;
}
