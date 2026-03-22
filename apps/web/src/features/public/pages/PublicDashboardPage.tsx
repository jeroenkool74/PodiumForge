import { useEffect, useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { getParticipantTypeLabel, getTournamentFormatLabel } from "@podiumforge/shared";
import { api } from "../../../api/client";
import type { DashboardRecord } from "../../../api/types";
import { BracketBoard } from "../../../components/BracketBoard";
import { DoubleEliminationBoard } from "../../../components/DoubleEliminationBoard";
import { PageShell } from "../../../components/PageShell";
import { PublicTournamentTabs } from "../../../components/PublicTournamentTabs";
import { StatusPill } from "../../../components/StatusPill";
import { dashboardSubtitle, tournamentPulse } from "../../tournaments/formatMeta";
import { standingPositionLabel } from "../../tournaments/standingPresentation";

type TvPanel = "live" | "bracket" | "podium";

function availableTvPanels(data: DashboardRecord | null, showBracketPanel: boolean): TvPanel[] {
  if (!data) return [];
  const panels: TvPanel[] = [];
  if (data.upcoming_matches.length || data.tournament_status !== "COMPLETED") {
    panels.push("live");
  }
  if (showBracketPanel) {
    panels.push("bracket");
  }
  panels.push("podium");
  return panels;
}

function nextTvPanel(current: TvPanel, panels: TvPanel[]) {
  const currentIndex = panels.indexOf(current);
  if (currentIndex === -1 || currentIndex === panels.length - 1) {
    return panels[0];
  }
  return panels[currentIndex + 1];
}

export function PublicDashboardPage({ immersive = false }: { immersive?: boolean }) {
  const { slug } = useParams();
  const [data, setData] = useState<DashboardRecord | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [tvPanel, setTvPanel] = useState<TvPanel>("live");
  const [autoRotate, setAutoRotate] = useState(true);

  useEffect(() => {
    let canceled = false;
    let timer: number | undefined;
    let refreshSeconds = 10;

    const load = async () => {
      try {
        const next = await api.getDashboard(slug ?? "");
        if (canceled) return;
        refreshSeconds = next.auto_refresh_seconds;
        setData(next);
        setError(null);
      } catch (err) {
        if (canceled) return;
        setError(err instanceof Error ? err.message : "Unknown error");
      } finally {
        if (canceled) return;
        setLoading(false);
        timer = window.setTimeout(load, refreshSeconds * 1000);
      }
    };

    void load();
    return () => {
      canceled = true;
      if (timer) window.clearTimeout(timer);
    };
  }, [slug]);

  const liveMode = data ? data.tournament_status !== "COMPLETED" : false;
  const podium = data?.podium ?? [];
  const formatLabel = data ? getTournamentFormatLabel(data.tournament_format) : "Tournament";
  const participantTypeLabel = data ? getParticipantTypeLabel(data.participant_type) : "Entrants";
  const isSingleBracket = data?.tournament_format === "BRACKET";
  const isDoubleElimination = data?.tournament_format === "DOUBLE_ELIMINATION";
  const showBracketPanel = isSingleBracket || isDoubleElimination;
  const tvPanels = useMemo(() => availableTvPanels(data, showBracketPanel), [data, showBracketPanel]);
  const tvPanelKey = tvPanels.join("|");

  useEffect(() => {
    setAutoRotate(true);
    setTvPanel("live");
  }, [slug, immersive]);

  useEffect(() => {
    if (!tvPanels.length) return;
    if (!tvPanels.includes(tvPanel)) {
      setTvPanel(tvPanels[0]);
    }
  }, [tvPanel, tvPanelKey]);

  useEffect(() => {
    if (!immersive || !autoRotate || tvPanels.length < 2) return;
    const timer = window.setInterval(() => {
      setTvPanel((current) => nextTvPanel(current, tvPanels));
    }, 12000);
    return () => window.clearInterval(timer);
  }, [immersive, autoRotate, tvPanelKey]);

  const matchTotals = useMemo(() => {
    if (!data) return { total: 0, completed: 0, remaining: 0 };
    const total = data.rounds.reduce((sum, round) => sum + round.matches.length, 0);
    const completed = data.rounds.reduce(
      (sum, round) => sum + round.matches.filter((match) => match.status === "COMPLETED").length,
      0,
    );
    return { total, completed, remaining: Math.max(total - completed, 0) };
  }, [data]);

  const featuredMatch = data?.upcoming_matches[0] ?? null;
  const secondaryMatches = data?.upcoming_matches.slice(1, 4) ?? [];
  const liveField = data?.tournament_status === "COMPLETED" ? podium.map((entry) => entry.display_name) : data?.qualified ?? [];

  const bracketPanel = data && isSingleBracket ? (
    <BracketBoard
      rounds={data.rounds}
      participantCount={data.participant_count}
      title={immersive ? "Bracket path" : "Live bracket"}
      matchHrefBuilder={(match) => `/matches/${match.id}`}
    />
  ) : data && isDoubleElimination ? (
    <DoubleEliminationBoard
      rounds={data.rounds}
      participantCount={data.participant_count}
      title={immersive ? "Dual bracket path" : "Live double-elimination bracket"}
      matchHrefBuilder={(match) => `/matches/${match.id}`}
    />
  ) : null;

  const currentSlateSection = data ? (
    <section className={`card dashboard-main-card ${immersive ? "tv-focus-card" : ""}`}>
      <div className="card-header-row">
        <div>
          <span className="eyebrow">Current slate</span>
          <h2>{featuredMatch?.name ?? data.current_round_name ?? "Final snapshot"}</h2>
          <p className="muted-text">{featuredMatch ? "TV mode now spotlights the next live table first." : "No live match is waiting on deck right now."}</p>
        </div>
        <span className="muted-text">{matchTotals.remaining} unresolved matches</span>
      </div>

      {featuredMatch ? (
        <div className={`tv-featured-grid ${immersive ? "immersive-featured-grid" : ""}`}>
          <article className="dashboard-match-card tv-featured-match-card">
            <div className="card-header-row">
              <div>
                <strong>{featuredMatch.name}</strong>
                <p className="muted-text">{featuredMatch.is_bye ? "Automatic advance" : `${featuredMatch.entrants.length} entrants`}</p>
              </div>
              <StatusPill value={featuredMatch.status} />
            </div>
            <div className="tv-featured-entrant-stack">
              {featuredMatch.entrants.map((entrant) => (
                <div key={entrant.participant_id} className="tv-featured-entrant-row">
                  <strong>{entrant.display_name}</strong>
                  <span className="muted-text">{entrant.seed_number ? `Seed #${entrant.seed_number}` : entrant.rank ? `#${entrant.rank}` : "Pending"}</span>
                </div>
              ))}
            </div>
            <div className="button-row compact-row">
              <Link to={`/matches/${featuredMatch.id}`}>Open match</Link>
            </div>
          </article>

          <div className="tv-secondary-match-stack">
            {secondaryMatches.length ? secondaryMatches.map((match) => (
              <article key={match.id} className="dashboard-match-card tv-secondary-match-card">
                <div className="card-header-row">
                  <div>
                    <strong>{match.name}</strong>
                    <p className="muted-text">{match.is_bye ? "Automatic advance" : `${match.entrants.length} entrants`}</p>
                  </div>
                  <StatusPill value={match.status} />
                </div>
                <div className="dashboard-entrant-row">
                  {match.entrants.map((entrant) => (
                    <span key={entrant.participant_id} className="dashboard-entrant-chip">
                      <strong>{entrant.display_name}</strong>
                      <span className="muted-text">{entrant.seed_number ? `Seed #${entrant.seed_number}` : "Pending"}</span>
                    </span>
                  ))}
                </div>
              </article>
            )) : (
              <div className="mini-card dashboard-empty-card">
                <strong>No backup slate</strong>
                <p className="muted-text">This featured match is the main table to watch right now.</p>
              </div>
            )}
          </div>
        </div>
      ) : (
        <div className="mini-card dashboard-empty-card">
          <strong>{data.tournament_status === "COMPLETED" ? "Event complete" : "No matches on deck"}</strong>
          <p className="muted-text">{data.tournament_status === "COMPLETED" ? "The final result is locked and the podium is ready to display." : "The next round has not been scheduled yet."}</p>
        </div>
      )}
    </section>
  ) : null;

  const standingsPanel = data ? (
    <section className={`dashboard-grid ${immersive ? "tv-dashboard-grid tv-dashboard-single-view" : ""}`}>
      <section className="card">
        <div className="card-header-row">
          <div>
            <span className="eyebrow">Leaderboard</span>
            <h2>Top standings</h2>
          </div>
        </div>
        {data.standings.length ? (
          <div className="results-grid leaderboard-grid">
            {data.standings.map((entry, index) => (
              <div key={entry.participant_id} className="result-row-card leaderboard-row-card">
                <div>
                  <strong>{standingPositionLabel(entry, index, liveMode)}</strong>
                  <div className="muted-text">{entry.latest_round_name ?? "Awaiting first result"}</div>
                </div>
                <div>
                  <strong>{entry.display_name}</strong>
                  <div className="muted-text">{entry.total_points} pts</div>
                </div>
                <StatusPill value={entry.current_status} />
              </div>
            ))}
          </div>
        ) : (
          <div className="mini-card dashboard-empty-card">
            <p className="muted-text">Standings will appear here once the first match result is saved.</p>
          </div>
        )}
      </section>

      <section className="card dashboard-side-card">
        {data.tournament_status === "COMPLETED" ? (
          <>
            <span className="eyebrow">Champion</span>
            <h2>{podium[0]?.display_name ?? "Pending"}</h2>
            <p className="muted-text">Final podium order is locked and ready for display.</p>
          </>
        ) : (
          <>
            <span className="eyebrow">Live field</span>
            <h2>{data.qualified.length} contenders</h2>
            <p className="muted-text">Active entrants are still in the running, while eliminated entrants have dropped out.</p>
          </>
        )}

        <div className="dashboard-name-cloud success-cloud">
          {liveField.length ? liveField.map((name) => (
            <span key={name} className="dashboard-name-pill">{name}</span>
          )) : <span className="muted-text">No names available yet.</span>}
        </div>

        <div className="dashboard-name-cloud muted-cloud">
          {data.tournament_status === "COMPLETED" ? (
            <p className="muted-text">The full finishing order is available from the standings page.</p>
          ) : data.eliminated.length ? (
            data.eliminated.map((name) => (
              <span key={name} className="dashboard-name-pill subdued-pill">{name}</span>
            ))
          ) : (
            <p className="muted-text">Nobody has been knocked out yet.</p>
          )}
        </div>
      </section>

      <section className="card podium-card dashboard-side-card">
        <span className="eyebrow">Podium</span>
        <h2>Top finishers</h2>
        {podium.length ? (
          <div className="podium-stack dashboard-podium-stack">
            {podium.map((entry, index) => (
              <div key={entry.participant_id} className="podium-step">
                <span>{standingPositionLabel(entry, index, false)}</span>
                <strong>{entry.display_name}</strong>
              </div>
            ))}
          </div>
        ) : (
          <p>Final podium appears here when the tournament is complete.</p>
        )}
      </section>
    </section>
  ) : null;

  return (
    <PageShell
      mode="public"
      title={data?.tournament_name ?? "Tournament dashboard"}
      subtitle={dashboardSubtitle(data?.tournament_format)}
      immersive={immersive}
      actions={
        slug ? (
          <div className="button-row compact-row">
            <Link to={immersive ? `/dashboard/${slug}` : `/dashboard/${slug}/tv`}>
              {immersive ? "Standard view" : "TV mode"}
            </Link>
          </div>
        ) : null
      }
    >
      {loading ? <div className="card">Loading dashboard...</div> : null}
      {error ? <div className="card error-card">{error}</div> : null}
      {data ? (
        <>
          {!immersive ? <PublicTournamentTabs slug={data.tournament_slug} current="dashboard" /> : null}

          <section className="card dashboard-spotlight-card">
            <div className="dashboard-spotlight-copy">
              <span className="eyebrow">{formatLabel}</span>
              <h2>{data.current_round_name ?? "Tournament complete"}</h2>
              <p>{tournamentPulse(data.tournament_format, data.tournament_status)}</p>
              {!immersive ? (
                <div className="button-row compact-row">
                  <Link to={`/tournaments/${data.tournament_slug}`}>Tournament overview</Link>
                  <Link to={`/tournaments/${data.tournament_slug}/standings`}>Standings</Link>
                </div>
              ) : null}
            </div>

            <div className="dashboard-stat-grid">
              <article className="mini-card dashboard-stat-card">
                <span className="eyebrow">Status</span>
                <strong>{data.tournament_status === "COMPLETED" ? "Complete" : "Live"}</strong>
                <StatusPill value={data.tournament_status} />
              </article>
              <article className="mini-card dashboard-stat-card">
                <span className="eyebrow">Field</span>
                <strong>{data.participant_count}</strong>
                <span className="muted-text">{participantTypeLabel}</span>
              </article>
              <article className="mini-card dashboard-stat-card">
                <span className="eyebrow">Resolved matches</span>
                <strong>{matchTotals.completed}</strong>
                <span className="muted-text">of {matchTotals.total}</span>
              </article>
              <article className="mini-card dashboard-stat-card">
                <span className="eyebrow">{data.tournament_status === "COMPLETED" ? "Podium" : "Still alive"}</span>
                <strong>{data.qualified.length || podium.length}</strong>
                <span className="muted-text">{data.tournament_status === "COMPLETED" ? "final podium slots" : "active contenders"}</span>
              </article>
            </div>
          </section>

          {immersive ? (
            <>
              <section className="card tv-control-card">
                <div className="card-header-row">
                  <div>
                    <span className="eyebrow">TV mode</span>
                    <h2>Rotation controls</h2>
                  </div>
                  <button type="button" className="ghost-button" onClick={() => setAutoRotate((current) => !current)}>
                    {autoRotate ? "Auto-rotate on" : "Auto-rotate off"}
                  </button>
                </div>
                <div className="tv-panel-switcher">
                  {tvPanels.map((panel) => (
                    <button
                      key={panel}
                      type="button"
                      className={`tv-panel-button ${tvPanel === panel ? "active-tv-panel" : "ghost-button"}`}
                      onClick={() => {
                        setTvPanel(panel);
                        setAutoRotate(false);
                      }}
                    >
                      {panel === "live" ? "Current slate" : panel === "bracket" ? "Bracket" : "Podium"}
                    </button>
                  ))}
                </div>
              </section>

              {tvPanel === "live" ? currentSlateSection : null}
              {tvPanel === "bracket" ? bracketPanel : null}
              {tvPanel === "podium" ? standingsPanel : null}
            </>
          ) : (
            <>
              {bracketPanel}
              {currentSlateSection}
              {standingsPanel}
            </>
          )}
        </>
      ) : null}
    </PageShell>
  );
}
