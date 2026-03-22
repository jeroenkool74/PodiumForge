import { FormEvent, useEffect, useMemo, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { api } from "../../../api/client";
import { useUnsavedChangesWarning } from "../../../app/useUnsavedChangesWarning";
import { useApiResource } from "../../../app/useApiResource";
import { BracketBoard } from "../../../components/BracketBoard";
import { DoubleEliminationBoard } from "../../../components/DoubleEliminationBoard";
import { MatchCard } from "../../../components/MatchCard";
import { PageShell } from "../../../components/PageShell";
import { StandingsTable } from "../../../components/StandingsTable";
import { TournamentFormatInsight } from "../../../components/TournamentFormatInsight";
import { TournamentHighlights } from "../../../components/TournamentHighlights";
import { placementPreviewLabel, pointsSchemeInputToList } from "../../tournaments/formatGuides";
import { advancementSummary, finalRoundLabel } from "../../tournaments/formatMeta";
import { useAuth } from "../../auth/AuthContext";
import { canDeleteTournament } from "../../auth/permissions";

const tieBreakOptions = [
  { value: "head_to_head", label: "Head-to-head" },
  { value: "total_points", label: "Total points" },
  { value: "best_rank", label: "Best rank" },
  { value: "score_total", label: "Score total" },
  { value: "matches_played", label: "Matches played" },
  { value: "average_rank", label: "Average rank" },
  { value: "display_name", label: "Display name" },
];

function formatPointsInput(pointsScheme: Array<{ placement: number; points: number }>) {
  return pointsScheme.map((item) => `${item.placement}:${item.points}`).join(", ");
}

export function TournamentEditPage() {
  const navigate = useNavigate();
  const { tournamentId } = useParams();
  const { token, user } = useAuth();
  const tournament = useApiResource(() => api.getManagedTournament(token ?? "", tournamentId ?? ""), [token, tournamentId]);
  const tieBreakRules = useApiResource(() => api.getTieBreakRules(token ?? "", tournamentId ?? ""), [token, tournamentId]);
  const [form, setForm] = useState({ name: "", description: "", is_public: true, status: "LIVE" });
  const [pointsInput, setPointsInput] = useState("");
  const [addParticipantName, setAddParticipantName] = useState("");
  const [addParticipantDirectoryId, setAddParticipantDirectoryId] = useState("");
  const [teamMembersInput, setTeamMembersInput] = useState("");
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [deleteArmed, setDeleteArmed] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [formReady, setFormReady] = useState(false);
  const [addingParticipant, setAddingParticipant] = useState(false);
  const [updatingPoints, setUpdatingPoints] = useState(false);
  const [recalculating, setRecalculating] = useState(false);
  const [creatingTieBreak, setCreatingTieBreak] = useState(false);
  const [pendingTieBreakType, setPendingTieBreakType] = useState("best_rank");
  const canDelete = canDeleteTournament(user);
  const tournamentDetail = tournament.data;
  const isSingleBracket = tournamentDetail?.format === "BRACKET";
  const isDoubleElimination = tournamentDetail?.format === "DOUBLE_ELIMINATION";
  const canAddParticipants = tournamentDetail?.can_add_participants ?? false;

  const directoryEntries = useApiResource(async () => {
    if (!token || !tournamentDetail) return [];
    return tournamentDetail.participant_type === "TEAM"
      ? api.listDirectoryTeams(token)
      : api.listDirectoryPlayers(token);
  }, [token, tournamentDetail?.participant_type]);

  const hasExistingResults = useMemo(
    () => Boolean(tournamentDetail?.stages.some((stage) => stage.rounds.some((round) => round.matches.some((match) => match.entrants.some((entrant) => entrant.rank !== null))))),
    [tournamentDetail],
  );

  const parsedPoints = useMemo(() => pointsSchemeInputToList(pointsInput), [pointsInput]);
  const isDirty = Boolean(
    tournamentDetail
    && (
      form.name !== tournamentDetail.name
      || form.description !== tournamentDetail.description
      || form.is_public !== tournamentDetail.is_public
      || form.status !== tournamentDetail.status
    ),
  );

  useUnsavedChangesWarning(
    formReady && isDirty && !saving && !generating && !deleting,
    "You have unsaved tournament changes. Leave this page anyway?",
  );

  useEffect(() => {
    if (!tournament.data) {
      setFormReady(false);
      return;
    }
    setForm({
      name: tournament.data.name,
      description: tournament.data.description,
      is_public: tournament.data.is_public,
      status: tournament.data.status,
    });
    setPointsInput(formatPointsInput(tournament.data.stages[0]?.points_scheme ?? []));
    setFormReady(true);
  }, [tournament.data]);

  async function refreshAll() {
    await Promise.all([tournament.refresh(), tieBreakRules.refresh(), directoryEntries.refresh()]);
  }

  async function handleSave(event: FormEvent) {
    event.preventDefault();
    if (saving) return;

    const trimmedName = form.name.trim();
    if (trimmedName.length < 3) {
      setError("Tournament name must be at least 3 characters.");
      return;
    }

    setMessage(null);
    setError(null);
    setSaving(true);
    try {
      await api.updateTournament(token ?? "", tournamentId ?? "", {
        ...form,
        name: trimmedName,
        description: form.description.trim(),
      });
      setMessage("Tournament saved.");
      await tournament.refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Save failed");
    } finally {
      setSaving(false);
    }
  }

  async function handleGenerateNextRound() {
    if (generating) return;
    setMessage(null);
    setError(null);
    setGenerating(true);
    try {
      await api.generateNextRound(token ?? "", tournamentId ?? "");
      setMessage("Next round generated.");
      await tournament.refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to generate next round");
    } finally {
      setGenerating(false);
    }
  }

  async function handleDeleteTournament() {
    if (deleting) return;

    setMessage(null);
    setError(null);
    setDeleting(true);
    try {
      await api.deleteTournament(token ?? "", tournamentId ?? "");
      navigate("/admin", { replace: true });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to delete tournament");
    } finally {
      setDeleting(false);
    }
  }

  async function handlePointsSave() {
    if (updatingPoints) return;
    if (!parsedPoints.length) {
      setError("Enter the points scheme as placement:points pairs such as 1:10, 2:7.");
      return;
    }
    setUpdatingPoints(true);
    setMessage(null);
    setError(null);
    try {
      await api.updatePointsScheme(token ?? "", tournamentId ?? "", parsedPoints);
      setMessage("Points scheme updated.");
      await tournament.refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to update points scheme");
    } finally {
      setUpdatingPoints(false);
    }
  }

  async function handleRecalculatePoints() {
    if (recalculating) return;
    setRecalculating(true);
    setMessage(null);
    setError(null);
    try {
      const result = await api.recalculatePoints(token ?? "", tournamentId ?? "");
      setMessage(result.message);
      await tournament.refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to recalculate points");
    } finally {
      setRecalculating(false);
    }
  }

  async function handleAddParticipant(event: FormEvent) {
    event.preventDefault();
    if (addingParticipant) return;
    const displayName = addParticipantName.trim();
    if (!displayName && !addParticipantDirectoryId) {
      setError("Choose a directory entry or enter a participant name.");
      return;
    }
    setAddingParticipant(true);
    setMessage(null);
    setError(null);
    try {
      await api.addParticipant(token ?? "", tournamentId ?? "", {
        display_name: displayName || "Directory entry",
        directory_entry_id: addParticipantDirectoryId || undefined,
        team_members: teamMembersInput.split("\n").map((item) => item.trim()).filter(Boolean),
      });
      setAddParticipantName("");
      setAddParticipantDirectoryId("");
      setTeamMembersInput("");
      setMessage("Participant added.");
      await tournament.refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to add participant");
    } finally {
      setAddingParticipant(false);
    }
  }

  async function handleCreateTieBreak() {
    if (creatingTieBreak) return;
    setCreatingTieBreak(true);
    setMessage(null);
    setError(null);
    try {
      const option = tieBreakOptions.find((item) => item.value === pendingTieBreakType);
      await api.createTieBreakRule(token ?? "", tournamentId ?? "", {
        name: option?.label ?? pendingTieBreakType,
        order_index: tieBreakRules.data?.length ?? 0,
        config: { rule_type: pendingTieBreakType },
      });
      setMessage("Tie-break rule added.");
      await refreshAll();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to add tie-break rule");
    } finally {
      setCreatingTieBreak(false);
    }
  }

  async function moveTieBreak(ruleId: string, currentIndex: number, direction: -1 | 1) {
    const nextIndex = currentIndex + direction;
    if (!tieBreakRules.data || nextIndex < 0 || nextIndex >= tieBreakRules.data.length) return;
    const current = tieBreakRules.data[currentIndex];
    setMessage(null);
    setError(null);
    try {
      await api.updateTieBreakRule(token ?? "", tournamentId ?? "", ruleId, {
        name: current.name,
        order_index: nextIndex,
        config: current.config,
      });
      await refreshAll();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to reorder tie-break rule");
    }
  }

  async function deleteTieBreak(ruleId: string) {
    setMessage(null);
    setError(null);
    try {
      await api.deleteTieBreakRule(token ?? "", tournamentId ?? "", ruleId);
      setMessage("Tie-break rule removed.");
      await refreshAll();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to delete tie-break rule");
    }
  }

  return (
    <PageShell mode="admin" title={tournamentDetail?.name ?? "Tournament management"} subtitle="Edit metadata, scoring, and live operations from one control room.">
      {tournament.loading ? <div className="card">Loading tournament...</div> : null}
      {tournament.error ? <div className="card error-card">{tournament.error}</div> : null}
      {tournamentDetail ? (
        <>
          <section className="card two-column-card">
            <form className="form-grid" onSubmit={handleSave}>
              <h2>Settings</h2>
              <label><span>Name</span><input required minLength={3} value={form.name} onChange={(event) => setForm((current) => ({ ...current, name: event.target.value }))} /></label>
              <label><span>Description</span><textarea rows={4} value={form.description} onChange={(event) => setForm((current) => ({ ...current, description: event.target.value }))} /></label>
              <label><span>Status</span><select value={form.status} onChange={(event) => setForm((current) => ({ ...current, status: event.target.value }))}><option value="LIVE">Live</option><option value="COMPLETED">Completed</option><option value="DRAFT">Draft</option></select></label>
              <label className="checkbox-row"><input type="checkbox" checked={form.is_public} onChange={(event) => setForm((current) => ({ ...current, is_public: event.target.checked }))} />Publicly visible</label>
              {message ? <div className="success-inline" role="status" aria-live="polite">{message}</div> : null}
              {error ? <div className="error-inline" role="alert">{error}</div> : null}
              <div className="button-row compact-row">
                <button type="submit" disabled={saving || generating}>{saving ? "Saving..." : "Save changes"}</button>
                {tournamentDetail.can_generate_next_round ? <button type="button" onClick={handleGenerateNextRound} disabled={saving || generating}>{generating ? "Generating..." : "Generate next round"}</button> : null}
                {tournamentDetail.is_public ? <Link to={`/tournaments/${tournamentDetail.slug}`}>Public page</Link> : <span className="muted-text">Private tournament</span>}
              </div>

              {canDelete ? (
                <div className="chip-panel danger-panel confirmation-panel">
                  <strong>Delete tournament</strong>
                  <p>This action cannot be undone. Deleting this tournament also removes its rounds, matches, standings, and public page.</p>
                  <div className="button-row compact-row">
                    {deleteArmed ? (
                      <>
                        <button type="button" className="danger-button" onClick={() => void handleDeleteTournament()} disabled={saving || generating || deleting}>{deleting ? "Deleting..." : "Confirm delete"}</button>
                        <button type="button" className="ghost-button" onClick={() => setDeleteArmed(false)} disabled={deleting}>Cancel</button>
                      </>
                    ) : (
                      <button type="button" className="danger-button" onClick={() => setDeleteArmed(true)} disabled={saving || generating || deleting}>Delete tournament</button>
                    )}
                  </div>
                </div>
              ) : null}
            </form>

            <div className="content-stack">
              <h2>Operations snapshot</h2>
              <div className="mini-card"><strong>Entrants</strong><span>{tournamentDetail.participants.length}</span></div>
              <TournamentHighlights
                format={tournamentDetail.format}
                status={tournamentDetail.status}
                standings={tournamentDetail.standings}
                activeNames={tournamentDetail.qualified}
                eliminatedNames={tournamentDetail.eliminated}
              />
            </div>
          </section>

          <section className="card two-column-card">
            <div className="content-stack">
              <div className="section-heading">
                <div>
                  <h2>Participants</h2>
                  <p className="muted-text">{canAddParticipants ? "Add one more entrant manually or from the directory." : "Participant additions are locked after match generation."}</p>
                </div>
              </div>
              {canAddParticipants ? (
                <form className="form-grid" onSubmit={(event) => void handleAddParticipant(event)}>
                  <label><span>Manual name</span><input value={addParticipantName} onChange={(event) => setAddParticipantName(event.target.value)} placeholder={tournamentDetail.participant_type === "TEAM" ? "New team name" : "New player name"} /></label>
                  <label>
                    <span>{tournamentDetail.participant_type === "TEAM" ? "Directory team" : "Directory player"}</span>
                    <select value={addParticipantDirectoryId} onChange={(event) => setAddParticipantDirectoryId(event.target.value)}>
                      <option value="">None selected</option>
                      {(directoryEntries.data ?? []).map((entry) => (
                        <option key={entry.id} value={entry.id}>{entry.name}</option>
                      ))}
                    </select>
                  </label>
                  {tournamentDetail.participant_type === "TEAM" ? (
                    <label><span>Roster members (one per line)</span><textarea rows={4} value={teamMembersInput} onChange={(event) => setTeamMembersInput(event.target.value)} /></label>
                  ) : null}
                  <div className="button-row compact-row">
                    <button type="submit" disabled={addingParticipant}>{addingParticipant ? "Adding..." : "Add participant"}</button>
                  </div>
                </form>
              ) : null}
            </div>

            <div className="content-stack">
              <h2>Current entrants</h2>
              <div className="participant-chip-grid">
                {tournamentDetail.participants.map((participant) => (
                  <article key={participant.id} className="mini-card participant-chip-card">
                    <strong>{participant.display_name}</strong>
                    <span className="muted-text">Seed {participant.seed_number ?? "-"}</span>
                    {participant.members.length ? <small>{participant.members.join(", ")}</small> : null}
                  </article>
                ))}
              </div>
            </div>
          </section>

          <section className="card two-column-card">
            <div className="content-stack">
              <div className="section-heading">
                <div>
                  <h2>Scoring</h2>
                  <p className="muted-text">Update the points scheme and recalculate historical results when needed.</p>
                </div>
              </div>
              <label>
                <span>Points scheme</span>
                <input value={pointsInput} onChange={(event) => setPointsInput(event.target.value)} />
              </label>
              <div className="points-preview-row">
                {parsedPoints.map((item) => (
                  <div key={`${item.placement}-${item.points}`} className="points-preview-pill">
                    <span>{placementPreviewLabel(item.placement)}</span>
                    <strong>{item.points} pts</strong>
                  </div>
                ))}
              </div>
              <div className="button-row compact-row">
                <button type="button" onClick={() => void handlePointsSave()} disabled={updatingPoints}>{updatingPoints ? "Saving..." : "Save points"}</button>
                {hasExistingResults ? <button type="button" className="ghost-button" onClick={() => void handleRecalculatePoints()} disabled={recalculating}>{recalculating ? "Recalculating..." : "Recalculate results"}</button> : null}
              </div>
            </div>

            <div className="content-stack">
              <div className="section-heading">
                <div>
                  <h2>Tie-break rules</h2>
                  <p className="muted-text">Carry over the v2 rule management flow while keeping the v1 standings engine.</p>
                </div>
              </div>
              <div className="button-row compact-row">
                <select value={pendingTieBreakType} onChange={(event) => setPendingTieBreakType(event.target.value)}>
                  {tieBreakOptions.map((option) => <option key={option.value} value={option.value}>{option.label}</option>)}
                </select>
                <button type="button" onClick={() => void handleCreateTieBreak()} disabled={creatingTieBreak}>{creatingTieBreak ? "Adding..." : "Add rule"}</button>
              </div>
              <div className="content-stack">
                {tieBreakRules.data?.map((rule, index) => (
                  <article key={rule.id} className="mini-card tie-break-card">
                    <div className="card-header-row">
                      <div>
                        <strong>{rule.name}</strong>
                        <div className="muted-text">{rule.config.rule_type.replace(/_/g, " ")}</div>
                      </div>
                      <div className="button-row compact-row">
                        <button type="button" className="ghost-button" onClick={() => void moveTieBreak(rule.id, index, -1)} disabled={index === 0}>Up</button>
                        <button type="button" className="ghost-button" onClick={() => void moveTieBreak(rule.id, index, 1)} disabled={index === (tieBreakRules.data?.length ?? 1) - 1}>Down</button>
                        <button type="button" className="danger-button" onClick={() => void deleteTieBreak(rule.id)}>Delete</button>
                      </div>
                    </div>
                  </article>
                ))}
              </div>
            </div>
          </section>

          <TournamentFormatInsight
            format={tournamentDetail.format}
            participantCount={tournamentDetail.participants.length}
            matchSize={tournamentDetail.stages[0]?.match_size ?? null}
            advanceCount={tournamentDetail.stages[0]?.advance_count ?? null}
            roundCount={tournamentDetail.stages[0]?.round_count ?? null}
            leaderboardMetric={tournamentDetail.stages[0]?.leaderboard_metric}
            scoreDirection={tournamentDetail.stages[0]?.score_direction}
            scoreLabel={tournamentDetail.stages[0]?.score_label}
            pointsScheme={tournamentDetail.stages[0]?.points_scheme ?? []}
            heading="Format explainer"
            collapsible
          />

          {isSingleBracket && tournamentDetail.stages[0]?.rounds.length ? (
            <BracketBoard
              rounds={tournamentDetail.stages[0].rounds}
              participantCount={tournamentDetail.participants.length}
              title={tournamentDetail.status === "COMPLETED" ? "Final bracket view" : "Admin bracket view"}
              matchHrefBuilder={(match) => `/admin/matches/${match.id}/entry`}
            />
          ) : null}

          {isDoubleElimination && tournamentDetail.stages[0]?.rounds.length ? (
            <DoubleEliminationBoard
              rounds={tournamentDetail.stages[0].rounds}
              participantCount={tournamentDetail.participants.length}
              title="Admin double-elimination view"
              matchHrefBuilder={(match) => `/admin/matches/${match.id}/entry`}
            />
          ) : null}

          {tournamentDetail.stages.map((stage) => (
            <section key={stage.id} className="card content-stack">
              <div className="card-header-row">
                <div>
                  <h2>{stage.name}</h2>
                  <p className="muted-text">{advancementSummary(stage.advancement_summary)}</p>
                </div>
              </div>
              {stage.rounds.map((round) => (
                <div key={round.id} className="subsection-block">
                  <div className="card-header-row">
                    <div>
                      <h3>{round.name}</h3>
                      <p className="muted-text">{round.is_final ? finalRoundLabel(tournamentDetail.format) : `Round ${round.number}`}</p>
                    </div>
                  </div>
                  <div className="card-grid">
                    {round.matches.map((match) => (
                      <MatchCard
                        key={match.id}
                        match={match}
                        publicLink={tournamentDetail.is_public ? `/matches/${match.id}` : undefined}
                        adminLink={`/admin/matches/${match.id}/entry`}
                      />
                    ))}
                  </div>
                </div>
              ))}
            </section>
          ))}

          <StandingsTable
            entries={tournamentDetail.standings}
            tournamentStatus={tournamentDetail.status}
            advancementKind={tournamentDetail.stages[0]?.advancement_kind}
            advanceCount={tournamentDetail.stages[0]?.advance_count}
            advancementSummary={tournamentDetail.stages[0]?.advancement_summary}
            tieBreakRules={tournamentDetail.stages[0]?.tie_break_rules}
            leaderboardMetric={tournamentDetail.stages[0]?.leaderboard_metric}
            scoreDirection={tournamentDetail.stages[0]?.score_direction}
            scoreLabel={tournamentDetail.stages[0]?.score_label}
          />
        </>
      ) : null}
    </PageShell>
  );
}
