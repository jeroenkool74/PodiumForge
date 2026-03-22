import { type FormEvent, useMemo, useState } from "react";
import { type TournamentFormat } from "@podiumforge/shared";
import { useNavigate } from "react-router-dom";
import { api } from "../../../api/client";
import { useApiResource } from "../../../app/useApiResource";
import { useUnsavedChangesWarning } from "../../../app/useUnsavedChangesWarning";
import { PageShell } from "../../../components/PageShell";
import { TournamentFormatInsight } from "../../../components/TournamentFormatInsight";
import { useAuth } from "../../auth/AuthContext";
import {
  getTournamentFormatGuide,
  placementPreviewLabel,
  pointsSchemeInputToList,
  tournamentFormatOrder,
} from "../../tournaments/formatGuides";
import {
  advanceCountHint,
  getTournamentSetupConfig,
  participantCountValidationError,
  participantRuleHint,
  usesFixedHeadToHeadMatches,
} from "../../tournaments/formatMeta";

interface TournamentCreateFormState {
  name: string;
  description: string;
  format: TournamentFormat;
  participant_type: "PLAYER" | "TEAM";
  match_size: number;
  advance_count: number;
  round_count: number;
  leaderboard_metric: "POINTS" | "SCORE";
  score_direction: "HIGHER_IS_BETTER" | "LOWER_IS_BETTER";
  score_label: string;
  participants: string;
  selected_directory_ids: string[];
  points: string;
  is_public: boolean;
}

function findDuplicateNames(names: string[]) {
  const seen = new Map<string, string>();
  const duplicates = new Set<string>();

  names.forEach((name) => {
    const normalized = name.trim().toLowerCase();
    if (!normalized) return;
    if (seen.has(normalized)) {
      duplicates.add(name.trim());
      return;
    }
    seen.set(normalized, name.trim());
  });

  return [...duplicates].sort((left, right) => left.localeCompare(right));
}

const initialForm: TournamentCreateFormState = {
  name: "",
  description: "",
  format: "FFA_ELIMINATION",
  participant_type: "PLAYER",
  match_size: 5,
  advance_count: 2,
  round_count: 3,
  leaderboard_metric: "POINTS",
  score_direction: "HIGHER_IS_BETTER",
  score_label: "Score",
  participants: "",
  selected_directory_ids: [],
  points: getTournamentSetupConfig("FFA_ELIMINATION").defaultPointsScheme,
  is_public: true,
};

export function TournamentCreatePage() {
  const { token } = useAuth();
  const navigate = useNavigate();
  const directoryPlayers = useApiResource(() => api.listDirectoryPlayers(token ?? ""), [token]);
  const directoryTeams = useApiResource(() => api.listDirectoryTeams(token ?? ""), [token]);
  const [form, setForm] = useState<TournamentCreateFormState>(initialForm);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const participantNames = useMemo(
    () => form.participants.split("\n").map((value) => value.trim()).filter(Boolean),
    [form.participants],
  );
  const selectedDirectoryEntries = useMemo(
    () => (form.participant_type === "TEAM" ? directoryTeams.data ?? [] : directoryPlayers.data ?? [])
      .filter((entry) => form.selected_directory_ids.includes(entry.id)),
    [directoryPlayers.data, directoryTeams.data, form.participant_type, form.selected_directory_ids],
  );
  const combinedParticipantNames = useMemo(
    () => [...participantNames, ...selectedDirectoryEntries.map((entry) => entry.name)],
    [participantNames, selectedDirectoryEntries],
  );
  const parsedPoints = useMemo(() => pointsSchemeInputToList(form.points), [form.points]);
  const duplicateParticipants = useMemo(() => findDuplicateNames(combinedParticipantNames), [combinedParticipantNames]);
  const currentSetup = getTournamentSetupConfig(form.format);
  const fixedHeadToHeadFormat = usesFixedHeadToHeadMatches(form.format);
  const optionalPointsFormat = currentSetup.pointsOptional;
  const runningLeaderboardFormat = form.format === "GROUP_POINTS" || form.format === "LEADERBOARD_SERIES";
  const selectedAdvanceCount = currentSetup.advanceCountMode === "hidden"
    ? null
    : currentSetup.advanceCountMode === "fixed-one"
      ? 1
      : form.advance_count;
  const selectedMatchSize = fixedHeadToHeadFormat ? 2 : form.match_size;
  const pointsRequired = !optionalPointsFormat && !(runningLeaderboardFormat && form.leaderboard_metric === "SCORE");
  const isDirty = JSON.stringify(form) !== JSON.stringify(initialForm);

  useUnsavedChangesWarning(isDirty && !submitting, "You have unsaved tournament setup changes. Leave this page anyway?");

  function handleFormatChange(nextFormat: TournamentFormat) {
    setForm((current) => {
      const currentFormatSetup = getTournamentSetupConfig(current.format);
      const nextFormatSetup = getTournamentSetupConfig(nextFormat);
      const pointsWereDefault = current.points === currentFormatSetup.defaultPointsScheme;

      return {
        ...current,
        format: nextFormat,
        match_size: usesFixedHeadToHeadMatches(nextFormat) ? 2 : usesFixedHeadToHeadMatches(current.format) && current.match_size === 2 ? 5 : current.match_size,
        advance_count:
          nextFormatSetup.advanceCountMode === "manual"
            ? currentFormatSetup.advanceCountMode === "manual"
              ? current.advance_count
              : 2
            : nextFormatSetup.advanceCountMode === "fixed-one"
              ? 1
              : 2,
        round_count: nextFormat === "LEADERBOARD_SERIES" ? current.round_count || 3 : current.round_count,
        points: pointsWereDefault ? nextFormatSetup.defaultPointsScheme : current.points,
      };
    });
  }

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    if (submitting) return;

    const trimmedName = form.name.trim();
    const trimmedDescription = form.description.trim();
    const effectiveAdvanceCount = selectedAdvanceCount ?? undefined;

    if (trimmedName.length < 3) {
      setError("Tournament name must be at least 3 characters.");
      return;
    }
    if (combinedParticipantNames.length < 2) {
      setError("Add at least two participants before creating the tournament.");
      return;
    }
    if (duplicateParticipants.length) {
      setError(`Participant names must be unique. Duplicate entries: ${duplicateParticipants.join(", ")}.`);
      return;
    }
    const participantRuleError = participantCountValidationError(form.format, combinedParticipantNames.length);
    if (participantRuleError) {
      setError(participantRuleError);
      return;
    }
    if (selectedMatchSize < 2) {
      setError("Match size must be at least 2.");
      return;
    }
    if (pointsRequired && !parsedPoints.length) {
      setError("Enter the points scheme as placement:points pairs, for example 1:10, 2:7, 3:5.");
      return;
    }
    if (
      currentSetup.advanceCountMode === "manual"
      && (effectiveAdvanceCount == null || !Number.isInteger(effectiveAdvanceCount) || effectiveAdvanceCount < 1)
    ) {
      setError("Advance count is required for this format.");
      return;
    }
    if (form.format === "LEADERBOARD_SERIES" && (!Number.isInteger(form.round_count) || form.round_count < 1)) {
      setError("Scheduled rounds must be at least 1.");
      return;
    }
    if (
      form.format === "FFA_ELIMINATION" &&
      effectiveAdvanceCount != null &&
      effectiveAdvanceCount >= selectedMatchSize
    ) {
      setError("Advance count must be smaller than the match size so at least one entrant is eliminated each round.");
      return;
    }

    setSubmitting(true);
    setError(null);
    try {
      const created = await api.createTournament(token ?? "", {
        name: trimmedName,
        description: trimmedDescription,
        format: form.format,
        participant_type: form.participant_type,
        match_size: selectedMatchSize,
        participants: participantNames,
        directory_player_ids: form.participant_type === "PLAYER" ? form.selected_directory_ids : [],
        directory_team_ids: form.participant_type === "TEAM" ? form.selected_directory_ids : [],
        points_scheme: parsedPoints,
        advance_count: effectiveAdvanceCount,
        round_count: form.format === "LEADERBOARD_SERIES" ? form.round_count : undefined,
        leaderboard_metric: form.leaderboard_metric,
        score_direction: form.score_direction,
        score_label: form.score_label.trim() || "Score",
        is_public: form.is_public,
      });
      navigate(`/admin/tournaments/${created.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to create tournament");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <PageShell
      mode="admin"
      title="Create tournament"
      subtitle="Pick the competition flow first, then tune the details before round one is generated."
    >
      <section className="card content-stack">
        <div className="section-heading">
          <div>
            <h2>Choose the tournament scheme</h2>
            <p className="muted-text">The format cards explain who advances, how points matter, and what the audience will see.</p>
          </div>
        </div>

        <div className="format-picker-grid">
          {tournamentFormatOrder.map((format) => {
            const guide = getTournamentFormatGuide(format);
            const isSelected = form.format === format;

            return (
              <button
                key={format}
                type="button"
                className={`format-option-card ${isSelected ? "selected-format-card" : ""}`}
                onClick={() => handleFormatChange(format)}
              >
                <span className="eyebrow">Scheme</span>
                <h3>{guide.label}</h3>
                <p>{guide.tagline}</p>
                <div className="format-option-preview">
                  {guide.preview.map((column) => (
                    <div key={`${format}-${column.label}`} className="format-option-column">
                      <strong>{column.label}</strong>
                      <span>{column.slots[0]}</span>
                    </div>
                  ))}
                </div>
              </button>
            );
          })}
        </div>
      </section>

      <TournamentFormatInsight
        format={form.format}
        participantCount={participantNames.length}
        matchSize={selectedMatchSize}
        advanceCount={selectedAdvanceCount}
        roundCount={form.format === "LEADERBOARD_SERIES" ? form.round_count : null}
        leaderboardMetric={form.leaderboard_metric}
        scoreDirection={form.score_direction}
        scoreLabel={form.score_label}
        pointsScheme={parsedPoints}
        heading="Selected flow"
        collapsible
      />

      <section className="card">
        <form className="form-grid" onSubmit={handleSubmit}>
          <div className="section-heading">
            <div>
              <h2>Tournament setup</h2>
              <p className="muted-text">Keep the operational fields close to the preview so the intent stays clear.</p>
            </div>
          </div>

          <label>
            <span>Name</span>
            <input required minLength={3} value={form.name} onChange={(event) => setForm((current) => ({ ...current, name: event.target.value }))} />
          </label>

          <label>
            <span>Description</span>
            <textarea rows={4} value={form.description} onChange={(event) => setForm((current) => ({ ...current, description: event.target.value }))} />
          </label>

          <div className="form-split">
            <label>
              <span>Entrant type</span>
              <select value={form.participant_type} onChange={(event) => setForm((current) => ({ ...current, participant_type: event.target.value as "PLAYER" | "TEAM", selected_directory_ids: [] }))}>
                <option value="PLAYER">Players</option>
                <option value="TEAM">Teams</option>
              </select>
            </label>

            <label>
              <span>{form.format === "STANDALONE_MATCH" ? "Players in the match" : fixedHeadToHeadFormat ? "Head-to-head match size" : "Match size"}</span>
              <input
                type="number"
                min={2}
                max={64}
                required
                disabled={fixedHeadToHeadFormat}
                value={selectedMatchSize}
                onChange={(event) => setForm((current) => ({ ...current, match_size: Number(event.target.value) }))}
              />
              <span className="field-hint">{fixedHeadToHeadFormat ? "This format uses head-to-head matches, so match size stays locked at 2." : "Use the group size you expect operators to seat at each table or heat."}</span>
            </label>

            <label>
              <span>Advance count</span>
              <input
                type="number"
                min={1}
                max={64}
                required={currentSetup.advanceCountMode === "manual"}
                disabled={currentSetup.advanceCountMode !== "manual"}
                value={selectedAdvanceCount ?? ""}
                onChange={(event) => setForm((current) => ({ ...current, advance_count: Number(event.target.value) }))}
              />
              <span className="field-hint">{advanceCountHint(form.format)}</span>
            </label>

            {form.format === "LEADERBOARD_SERIES" ? (
              <label>
                <span>Scheduled rounds</span>
                <input
                  type="number"
                  min={1}
                  max={64}
                  required
                  value={form.round_count}
                  onChange={(event) => setForm((current) => ({ ...current, round_count: Number(event.target.value) }))}
                />
                <span className="field-hint">Everyone stays active until this fixed number of rounds is complete.</span>
              </label>
            ) : null}

            {runningLeaderboardFormat ? (
              <label>
                <span>Leaderboard basis</span>
                <select value={form.leaderboard_metric} onChange={(event) => setForm((current) => ({ ...current, leaderboard_metric: event.target.value as "POINTS" | "SCORE" }))}>
                  <option value="POINTS">Total points</option>
                  <option value="SCORE">Total score</option>
                </select>
                <span className="field-hint">Choose whether the running table follows awarded points or the sum of the score field.</span>
              </label>
            ) : null}

            <label>
              <span>Score direction</span>
              <select value={form.score_direction} onChange={(event) => setForm((current) => ({ ...current, score_direction: event.target.value as "HIGHER_IS_BETTER" | "LOWER_IS_BETTER" }))}>
                <option value="HIGHER_IS_BETTER">Higher is better</option>
                <option value="LOWER_IS_BETTER">Lower is better</option>
              </select>
              <span className="field-hint">Controls how score values break ties and how score-based leaderboards rank entrants.</span>
            </label>

            <label>
              <span>Score label</span>
              <input value={form.score_label} maxLength={40} onChange={(event) => setForm((current) => ({ ...current, score_label: event.target.value }))} />
              <span className="field-hint">Rename the numeric match field for your event, such as Score, Time, or Differential.</span>
            </label>
          </div>

          <label>
              <span>{optionalPointsFormat ? "Points scheme (optional live-table scoring)" : "Points scheme"}</span>
            <input required={pointsRequired} value={form.points} onChange={(event) => setForm((current) => ({ ...current, points: event.target.value }))} />
            <span className="field-hint">Use comma-separated `placement:points` pairs such as `1:10, 2:7, 3:5`.</span>
          </label>

          <div className="points-preview-row">
            {parsedPoints.length ? (
              parsedPoints.map((item) => (
                <div key={`${item.placement}-${item.points}`} className="points-preview-pill">
                  <span>{placementPreviewLabel(item.placement)}</span>
                  <strong>{item.points} pts</strong>
                </div>
              ))
            ) : (
              <div className="mini-card note-card">
                <strong>Points preview unavailable</strong>
                <p>Enter values in `placement:points` format to see the scoring chips update live.</p>
              </div>
            )}
          </div>

          <label>
            <span>Participants (one per line)</span>
            <textarea
              rows={10}
              value={form.participants}
              onChange={(event) => setForm((current) => ({ ...current, participants: event.target.value }))}
              placeholder="Nyx&#10;Carter&#10;Mira&#10;Sol&#10;Vega"
            />
            <span className="field-hint">{combinedParticipantNames.length ? `${combinedParticipantNames.length} entrants ready for seeding across manual entries and directory picks.` : "Add at least two names or directory selections to preview the structure accurately."}</span>
            {participantRuleHint(form.format) ? <span className="field-hint">{participantRuleHint(form.format)}</span> : null}
            {duplicateParticipants.length ? <span className="field-hint">Duplicate names detected: {duplicateParticipants.join(", ")}.</span> : null}
          </label>

          <div className="content-stack">
            <div className="section-heading">
              <div>
                <h2>{form.participant_type === "TEAM" ? "Team directory" : "Player directory"}</h2>
                <p className="muted-text">Mix manual names with reusable directory entries from version 2 style workflows.</p>
              </div>
            </div>
            <div className="directory-member-grid">
              {form.participant_type === "TEAM"
                ? (directoryTeams.data ?? []).map((entry) => (
                    <label key={entry.id} className="directory-member-option directory-selection-option">
                      <input
                        type="checkbox"
                        checked={form.selected_directory_ids.includes(entry.id)}
                        onChange={() => setForm((current) => ({ ...current, selected_directory_ids: current.selected_directory_ids.includes(entry.id) ? current.selected_directory_ids.filter((item) => item !== entry.id) : [...current.selected_directory_ids, entry.id] }))}
                      />
                      <span>{entry.name}</span>
                      {entry.members.length ? <small>{entry.members.map((member) => member.name).join(", ")}</small> : null}
                    </label>
                  ))
                : (directoryPlayers.data ?? []).map((entry) => (
                    <label key={entry.id} className="directory-member-option directory-selection-option">
                      <input
                        type="checkbox"
                        checked={form.selected_directory_ids.includes(entry.id)}
                        onChange={() => setForm((current) => ({ ...current, selected_directory_ids: current.selected_directory_ids.includes(entry.id) ? current.selected_directory_ids.filter((item) => item !== entry.id) : [...current.selected_directory_ids, entry.id] }))}
                      />
                      <span>{entry.name}</span>
                    </label>
                  ))}
              {!((form.participant_type === "TEAM" ? directoryTeams.data : directoryPlayers.data) ?? []).length ? (
                <div className="mini-card note-card">
                  <strong>No reusable entries yet</strong>
                  <p>Create players or teams from the admin directory pages, then return here to seed tournaments from them.</p>
                </div>
              ) : null}
            </div>
          </div>

          <label className="checkbox-row">
            <input type="checkbox" checked={form.is_public} onChange={(event) => setForm((current) => ({ ...current, is_public: event.target.checked }))} />
            Visible on the public dashboard
          </label>

          {error ? <div className="error-inline" role="alert">{error}</div> : null}
          <button type="submit" disabled={submitting}>{submitting ? "Creating..." : "Create tournament"}</button>
        </form>
      </section>

    </PageShell>
  );
}
