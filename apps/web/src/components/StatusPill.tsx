import { getStatusLabel } from "@podiumforge/shared";

export function StatusPill({ value }: { value: string }) {
  return <span className={`status-pill status-${value.toLowerCase()}`}>{getStatusLabel(value)}</span>;
}
