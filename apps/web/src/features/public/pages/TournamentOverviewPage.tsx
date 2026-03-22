import { Link, useParams, useSearchParams } from "react-router-dom";
import { getParticipantTypeLabel, getTournamentFormatLabel } from "@podiumforge/shared";
import { api } from "../../../api/client";
import { useApiResource } from "../../../app/useApiResource";
import { BracketBoard } from "../../../components/BracketBoard";
import { DoubleEliminationBoard } from "../../../components/DoubleEliminationBoard";
import { MatchCard } from "../../../components/MatchCard";
import { PageShell } from "../../../components/PageShell";
import { PublicTournamentTabs } from "../../../components/PublicTournamentTabs";
import { StatusPill } from "../../../components/StatusPill";
import { TournamentHighlights } from "../../../components/TournamentHighlights";
import { advancementSummary, finalRoundLabel, leaderboardMetricLabel, scoreDirectionLabel, tieBreakLabel } from "../../tournaments/formatMeta";

export function TournamentOverviewPage() {
  const { slug } = useParams();
  const [searchParams] = useSearchParams();
  const { data, loading, error } = useApiResource(() => api.getPublicTournament(slug ?? ""), [slug]);
  const isDoubleElimination = data?.format === "DOUBLE_ELIMINATION";
  const isSingleBracket = data?.format === "BRACKET";
  const isTeamTournament = data?.participant_type === "TEAM";
  const activeTab = searchParams.get("tab") === "rounds" ? "rounds" : "overview";
  const primaryStage = data?.stages[0];
  const stageRoundCount = primaryStage?.rounds.length ?? 0;
  const stageMatchCount = primaryStage?.rounds.reduce((sum, round) => sum + round.matches.length, 0) ?? 0;

  return (
    <PageShell
      mode="public"
      title={data?.name ?? "Tournament overview"}
      subtitle={data?.description}
      actions={data ? <Link to={`/dashboard/${data.slug}/tv`}>TV mode</Link> : undefined}
    >
      {loading ? <div className="card">Loading tournament...</div> : null}
      {error ? <div className="card error-card">{error}</div> : null}
      {data ? (
        <>
          <PublicTournamentTabs slug={data.slug} current={activeTab} showTeams={isTeamTournament} />

          <section className="card feature-card">
            <div className="meta-strip">
              <div>
                <span className="eyebrow">Format</span>
                <strong>{getTournamentFormatLabel(data.format)}</strong>
              </div>
              <div>
                <span className="eyebrow">Entrant type</span>
                <strong>{getParticipantTypeLabel(data.participant_type)}</strong>
              </div>
              <div>
                <span className="eyebrow">Status</span>
                <StatusPill value={data.status} />
              </div>
              <div>
                <span className="eyebrow">Live views</span>
                <div className="button-row compact-row">
                  <Link to={`/tournaments/${data.slug}/standings`}>Standings</Link>
                  <Link to={`/dashboard/${data.slug}/tv`}>TV mode</Link>
                </div>
              </div>
            </div>
            <TournamentHighlights
              format={data.format}
              status={data.status}
              standings={data.standings}
              activeNames={data.qualified}
              eliminatedNames={data.eliminated}
            />
          </section>

          {activeTab === "overview" ? (
            <section className="feature-grid">
              <article className="card overview-summary-card">
                <span className="eyebrow">Overview</span>
                <h2>Main stage snapshot</h2>
                <div className="metric-grid compact-grid">
                  <div className="mini-card format-metric-card">
                    <strong>Rounds</strong>
                    <span>{stageRoundCount || "-"}</span>
                  </div>
                  <div className="mini-card format-metric-card">
                    <strong>Matches</strong>
                    <span>{stageMatchCount || "-"}</span>
                  </div>
                  <div className="mini-card format-metric-card">
                    <strong>Match size</strong>
                    <span>{primaryStage?.match_size ?? "-"}</span>
                  </div>
                  <div className="mini-card format-metric-card">
                    <strong>Leaderboard</strong>
                    <span>{leaderboardMetricLabel(primaryStage?.leaderboard_metric)}</span>
                  </div>
                  <div className="mini-card format-metric-card">
                    <strong>{primaryStage?.score_label ?? "Score"}</strong>
                    <span>{scoreDirectionLabel(primaryStage?.score_direction)}</span>
                  </div>
                </div>
                <div className="mini-card note-card">
                  <strong>Advancement story</strong>
                  <p>{advancementSummary(primaryStage?.advancement_summary, "No advancement rule configured yet.")}</p>
                </div>
                <div className="mini-card note-card">
                  <strong>Tie-break lead</strong>
                  <p>{tieBreakLabel(primaryStage?.tie_break_rules?.[0])}</p>
                </div>
              </article>

              <article className="card overview-summary-card">
                <span className="eyebrow">Quick links</span>
                <h2>Follow the live flow</h2>
                <div className="button-row compact-row">
                  <Link to={`/tournaments/${data.slug}?tab=rounds`}>Open rounds</Link>
                  <Link to={`/tournaments/${data.slug}/standings`}>Open standings</Link>
                  <Link to={`/dashboard/${data.slug}/tv`}>Open TV mode</Link>
                  {isTeamTournament ? <Link to={`/tournaments/${data.slug}/teams`}>Open teams</Link> : null}
                  <Link to={`/tournaments/${data.slug}/print`}>Print standings</Link>
                </div>
                <div className="content-stack">
                  {data.stages.map((stage) => (
                    <div key={stage.id} className="mini-card note-card">
                      <strong>{stage.name}</strong>
                      <p>{advancementSummary(stage.advancement_summary)}</p>
                    </div>
                  ))}
                </div>
              </article>
            </section>
          ) : null}

          {activeTab === "rounds" ? (
            <section className="content-stack">
              {isSingleBracket && data.stages[0]?.rounds.length ? (
                <BracketBoard
                  rounds={data.stages[0].rounds}
                  participantCount={data.participants.length}
                  title={data.status === "COMPLETED" ? "Final bracket" : "Live bracket"}
                  matchHrefBuilder={(match) => `/matches/${match.id}`}
                />
              ) : null}

              {isDoubleElimination && data.stages[0]?.rounds.length ? (
                <DoubleEliminationBoard
                  rounds={data.stages[0].rounds}
                  participantCount={data.participants.length}
                  matchHrefBuilder={(match) => `/matches/${match.id}`}
                />
              ) : null}

              {data.stages.map((stage) => (
                <div key={stage.id} className="card">
                  <div className="card-header-row">
                    <div>
                      <h2>{stage.name}</h2>
                      <p className="muted-text">{advancementSummary(stage.advancement_summary)}</p>
                    </div>
                    <span className="eyebrow">Match size {stage.match_size ?? "-"}</span>
                  </div>
                  <div className="content-stack">
                    {stage.rounds.map((round) => (
                      <section key={round.id} className="subsection-block">
                        <div className="card-header-row">
                          <div>
                            <h3>{round.name}</h3>
                            <p className="muted-text">{round.is_final ? finalRoundLabel(data.format) : `Round ${round.number}`}</p>
                          </div>
                          <div className="button-row compact-row">
                            <StatusPill value={round.status} />
                            <Link to={`/tournaments/${data.slug}/rounds/${round.id}`}>Round page</Link>
                          </div>
                        </div>
                        <div className="card-grid">
                          {round.matches.map((match) => (
                            <MatchCard key={match.id} match={match} publicLink={`/matches/${match.id}`} />
                          ))}
                        </div>
                      </section>
                    ))}
                  </div>
                </div>
              ))}
            </section>
          ) : null}
        </>
      ) : null}
    </PageShell>
  );
}
