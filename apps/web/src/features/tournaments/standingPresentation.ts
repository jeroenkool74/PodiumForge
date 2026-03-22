import { placementLabel } from "@podiumforge/shared";
import type { StandingEntry } from "../../api/types";

export function isLiveStandingStatus(status: string) {
  return status === "ACTIVE" || status === "QUALIFIED";
}

export function hasLiveStandings(entries: StandingEntry[]) {
  return entries.some((entry) => isLiveStandingStatus(entry.current_status));
}

export function standingPositionLabel(
  entry: StandingEntry,
  index: number,
  liveMode: boolean,
) {
  if (liveMode && isLiveStandingStatus(entry.current_status)) {
    return `#${index + 1}`;
  }

  return placementLabel(entry.final_placement ?? index + 1);
}

export function podiumEntries(entries: StandingEntry[]) {
  return entries
    .filter((entry) => entry.final_placement !== null && entry.final_placement <= 3)
    .sort(
      (left, right) =>
        (left.final_placement ?? Number.MAX_SAFE_INTEGER) -
        (right.final_placement ?? Number.MAX_SAFE_INTEGER),
    );
}
