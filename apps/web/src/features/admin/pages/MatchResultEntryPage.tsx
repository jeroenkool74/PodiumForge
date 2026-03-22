import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api } from "../../../api/client";
import { useApiResource } from "../../../app/useApiResource";
import { useUnsavedChangesWarning } from "../../../app/useUnsavedChangesWarning";
import { PageShell } from "../../../components/PageShell";
import { useAuth } from "../../auth/AuthContext";

interface EditableEntrant {
  participant_id: string;
  display_name: string;
  rank: string;
  score: string;
  tie_group: string;
}

function validateResultShape(rows: Array<{ display_name: string; rank: number; tie_group?: number }>) {
  const groupedByRank = new Map<number, Array<{ display_name: string; tie_group?: number }>>();

  for (const row of rows) {
    const group = groupedByRank.get(row.rank) ?? [];
    group.push({ display_name: row.display_name, tie_group: row.tie_group });
    groupedByRank.set(row.rank, group);
  }

  let expectedRank = 1;
  const usedTieGroups = new Set<number>();

  for (const rank of [...groupedByRank.keys()].sort((left, right) => left - right)) {
    const group = groupedByRank.get(rank) ?? [];
    if (rank !== expectedRank) {
      return "Places must stay contiguous. Reuse the same place number only when entrants are tied.";
    }

    if (group.length === 1) {
      if (group[0]?.tie_group !== undefined) {
        return `Clear the tie group for ${group[0].display_name} unless that entrant shares the place with someone else.`;
      }
    } else {
      const tieGroups = new Set(group.map((item) => item.tie_group).filter((value): value is number => value !== undefined));
      if (tieGroups.size !== 1 || group.some((item) => item.tie_group === undefined)) {
        return `Entrants sharing place ${rank} must all use the same tie group.`;
      }

      const tieGroup = [...tieGroups][0];
      if (usedTieGroups.has(tieGroup)) {
        return `Tie group ${tieGroup} is already used by another finishing place.`;
      }
      usedTieGroups.add(tieGroup);
    }

    expectedRank += group.length;
  }

  return null;
}

function parsePositiveInteger(value: string) {
  const normalized = value.trim();
  if (!normalized) return null;
  const parsed = Number(normalized);
  if (!Number.isInteger(parsed) || parsed < 1) return null;
  return parsed;
}

function parseOptionalNumber(value: string) {
  const normalized = value.trim();
  if (!normalized) return { value: undefined, valid: true };
  const parsed = Number(normalized);
  if (!Number.isFinite(parsed)) return { value: undefined, valid: false };
  return { value: parsed, valid: true };
}

export function MatchResultEntryPage() {
  const { matchId } = useParams();
  const { token } = useAuth();
  const match = useApiResource(() => api.getManagedMatch(token ?? "", matchId ?? ""), [token, matchId]);
  const [rows, setRows] = useState<EditableEntrant[]>([]);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [scheduledAt, setScheduledAt] = useState("");
  const [scheduling, setScheduling] = useState(false);
  const [clearing, setClearing] = useState(false);
  const [clearConfirm, setClearConfirm] = useState(false);
  const isBye = match.data?.is_bye ?? false;
  const resultsLocked = match.data?.results_locked ?? false;
  const canUseQuickOrdering = rows.every((row, index) => row.rank.trim() === `${index + 1}` && !row.tie_group.trim());
  const initialRowsKey = [...(match.data?.entrants ?? [])]
    .sort((left, right) => (left.rank ?? left.slot_number) - (right.rank ?? right.slot_number))
    .map((entrant, index) => `${entrant.participant_id}:${entrant.rank ?? index + 1}:${entrant.score ?? ""}:${entrant.tie_group ?? ""}`)
    .join("|");
  const currentRowsKey = rows.map((row) => `${row.participant_id}:${row.rank.trim()}:${row.score.trim()}:${row.tie_group.trim()}`).join("|");

  useUnsavedChangesWarning(
    !isBye && !resultsLocked && !submitting && Boolean(rows.length) && currentRowsKey !== initialRowsKey,
    "You have unsaved match results. Leave this page anyway?",
  );

  useEffect(() => {
    if (!match.data) return;
    const initial = [...match.data.entrants]
      .sort((left, right) => (left.rank ?? left.slot_number) - (right.rank ?? right.slot_number))
      .map((entrant, index) => ({
        participant_id: entrant.participant_id,
        display_name: entrant.display_name,
        rank: String(entrant.rank ?? index + 1),
        score: entrant.score?.toString() ?? "",
        tie_group: entrant.tie_group?.toString() ?? "",
      }));
    setRows(initial);
  }, [match.data]);

  useEffect(() => {
    if (!match.data?.scheduled_at) {
      setScheduledAt("");
      return;
    }
    const date = new Date(match.data.scheduled_at);
    const local = new Date(date.getTime() - date.getTimezoneOffset() * 60000);
    setScheduledAt(local.toISOString().slice(0, 16));
  }, [match.data?.scheduled_at]);

  function moveRow(index: number, direction: -1 | 1) {
    setRows((current) => {
      const nextIndex = index + direction;
      if (nextIndex < 0 || nextIndex >= current.length) return current;
      const next = [...current];
      [next[index], next[nextIndex]] = [next[nextIndex], next[index]];
      return next.map((row, rowIndex) => ({ ...row, rank: `${rowIndex + 1}` }));
    });
  }

  async function handleSave() {
    if (submitting) return;
    if (isBye) return;
    if (resultsLocked) return;

    const normalizedRows = [] as Array<{ participant_id: string; display_name: string; rank: number; score?: number; tie_group?: number }>;

    for (const row of rows) {
      const rank = parsePositiveInteger(row.rank);
      if (!rank) {
        setError(`Enter a valid finishing place for ${row.display_name}.`);
        setMessage(null);
        return;
      }

      const score = parseOptionalNumber(row.score);
      if (!score.valid) {
        setError(`Score for ${row.display_name} must be numeric if provided.`);
        setMessage(null);
        return;
      }

      const tieGroup = parseOptionalNumber(row.tie_group);
      if (!tieGroup.valid || (tieGroup.value !== undefined && (!Number.isInteger(tieGroup.value) || tieGroup.value < 1))) {
        setError(`Tie group for ${row.display_name} must be a positive whole number if provided.`);
        setMessage(null);
        return;
      }

      normalizedRows.push({
        participant_id: row.participant_id,
        display_name: row.display_name,
        rank,
        score: score.value,
        tie_group: tieGroup.value,
      });
    }

    const resultShapeError = validateResultShape(normalizedRows);
    if (resultShapeError) {
      setError(resultShapeError);
      setMessage(null);
      return;
    }

    setSubmitting(true);
    setMessage(null);
    setError(null);
    try {
      await api.saveMatchResults(token ?? "", matchId ?? "", {
        results: normalizedRows.map(({ display_name: _displayName, ...result }) => result),
      });
      setMessage("Results saved. Standings and progression refreshed.");
      await match.refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to save results");
    } finally {
      setSubmitting(false);
    }
  }

  async function handleScheduleSave() {
    if (scheduling) return;
    setScheduling(true);
    setMessage(null);
    setError(null);
    try {
      await api.scheduleMatch(token ?? "", matchId ?? "", scheduledAt ? new Date(scheduledAt).toISOString() : null);
      setMessage(scheduledAt ? "Match schedule saved." : "Match schedule cleared.");
      await match.refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to update the schedule");
    } finally {
      setScheduling(false);
    }
  }

  async function handleScheduleClear() {
    if (scheduling) return;
    setScheduling(true);
    setMessage(null);
    setError(null);
    try {
      await api.scheduleMatch(token ?? "", matchId ?? "", null);
      setScheduledAt("");
      setMessage("Match schedule cleared.");
      await match.refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to clear the schedule");
    } finally {
      setScheduling(false);
    }
  }

  async function handleClearResults() {
    if (clearing) return;
    setClearing(true);
    setMessage(null);
    setError(null);
    try {
      await api.clearMatchResults(token ?? "", matchId ?? "");
      setClearConfirm(false);
      setMessage("Match results cleared.");
      await match.refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to clear results");
    } finally {
      setClearing(false);
    }
  }

  return (
    <PageShell mode="admin" title={match.data?.name ?? "Match entry"} subtitle="Fast manual result entry with ranked finishing order, optional scores, and tie-group support.">
      {match.loading ? <div className="card">Loading match...</div> : null}
      {match.error ? <div className="card error-card">{match.error}</div> : null}
      {match.data ? (
        <form className="card content-stack" onSubmit={(event) => { event.preventDefault(); void handleSave(); }}>
          <div className="card-header-row">
            <div>
              <h2>{match.data.name}</h2>
              <p className="muted-text">Use the arrows for quick ordering, or type place numbers directly for ties. Shared places must also share one tie group.</p>
            </div>
            <div className="button-row compact-row">
              <Link to={`/admin/tournaments/${match.data.tournament_id}`}>Back to tournament</Link>
              <Link to="/admin">Back to admin</Link>
            </div>
          </div>
          <div className="chip-panel inline-form-panel">
            <div>
              <strong>Schedule</strong>
              <p className="muted-text">Store the planned start time before results are entered.</p>
            </div>
            <div className="button-row compact-row">
              <input type="datetime-local" value={scheduledAt} onChange={(event) => setScheduledAt(event.target.value)} />
              <button type="button" onClick={() => void handleScheduleSave()} disabled={scheduling}>{scheduling ? "Saving..." : "Save schedule"}</button>
              {match.data.scheduled_at ? <button type="button" className="ghost-button" onClick={() => void handleScheduleClear()} disabled={scheduling}>Clear</button> : null}
            </div>
          </div>
          {isBye ? (
            <div className="chip-panel">
              <strong>Automatic bye</strong>
              <p className="muted-text">This match advanced automatically, so there is nothing to enter manually.</p>
            </div>
          ) : resultsLocked ? (
            <div className="chip-panel danger-panel confirmation-panel">
              <strong>Results locked</strong>
              <p>This match can no longer be edited because a later round already exists. Return to the latest live round to continue operations.</p>
            </div>
          ) : (
            <div className="result-entry-stack">
              {rows.map((row, index) => (
                <div key={row.participant_id} className="entry-editor-row">
                  <div>
                    <strong>{row.display_name}</strong>
                    <div className="button-row compact-row">
                      <button type="button" className="ghost-button" onClick={() => moveRow(index, -1)} disabled={index === 0 || !canUseQuickOrdering}>Up</button>
                      <button type="button" className="ghost-button" onClick={() => moveRow(index, 1)} disabled={index === rows.length - 1 || !canUseQuickOrdering}>Down</button>
                    </div>
                  </div>
                  <label>
                    <span>Place</span>
                    <input type="number" min={1} required value={row.rank} onChange={(event) => setRows((current) => current.map((item) => item.participant_id === row.participant_id ? { ...item, rank: event.target.value } : item))} />
                  </label>
                  <label>
                    <span>Score</span>
                    <input type="number" step="any" inputMode="decimal" value={row.score} onChange={(event) => setRows((current) => current.map((item) => item.participant_id === row.participant_id ? { ...item, score: event.target.value } : item))} />
                  </label>
                  <label>
                    <span>Tie group</span>
                    <input type="number" min={1} inputMode="numeric" value={row.tie_group} onChange={(event) => setRows((current) => current.map((item) => item.participant_id === row.participant_id ? { ...item, tie_group: event.target.value } : item))} />
                  </label>
                </div>
              ))}
            </div>
          )}
          {!isBye && !resultsLocked && !canUseQuickOrdering ? <div className="chip-panel"><p className="muted-text">Quick ordering is disabled after you enter custom places or tie groups so your manual ranking stays intact.</p></div> : null}
          {message ? <div className="success-inline" role="status" aria-live="polite">{message}</div> : null}
          {error ? <div className="error-inline" role="alert">{error}</div> : null}
          {!isBye && !resultsLocked ? (
            <div className="button-row">
              <button type="submit" disabled={submitting}>{submitting ? "Saving..." : "Save results"}</button>
              {match.data.entrants.some((entrant) => entrant.rank !== null) ? <button type="button" className="danger-button" onClick={() => setClearConfirm(true)} disabled={clearing}>{clearing ? "Clearing..." : "Clear results"}</button> : null}
            </div>
          ) : null}
          {clearConfirm ? (
            <div className="chip-panel danger-panel confirmation-panel">
              <strong>Clear saved results?</strong>
              <p>This resets the match back to a scheduled state and recalculates the tournament standings.</p>
              <div className="button-row compact-row">
                <button type="button" className="danger-button" onClick={() => void handleClearResults()} disabled={clearing}>{clearing ? "Clearing..." : "Confirm clear"}</button>
                <button type="button" className="ghost-button" onClick={() => setClearConfirm(false)} disabled={clearing}>Cancel</button>
              </div>
            </div>
          ) : null}
        </form>
      ) : null}
    </PageShell>
  );
}
