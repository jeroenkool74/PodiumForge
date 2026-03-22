import { Link, useParams } from "react-router-dom";
import { api } from "../../../api/client";
import { useApiResource } from "../../../app/useApiResource";
import { PageShell } from "../../../components/PageShell";
import { PublicTournamentTabs } from "../../../components/PublicTournamentTabs";
import { StandingsTable } from "../../../components/StandingsTable";

export function StandingsPage() {
  const { slug } = useParams();
  const detail = useApiResource(() => api.getPublicTournament(slug ?? ""), [slug]);
  const standings = useApiResource(() => api.getPublicStandings(slug ?? ""), [slug]);
  const primaryStage = detail.data?.stages[0];
  const showTeams = detail.data?.participant_type === "TEAM";

  return (
    <PageShell
      mode="public"
      title={detail.data ? `${detail.data.name} standings` : "Standings"}
      subtitle="Current rankings, points, and overall placement."
      actions={detail.data ? <Link to={`/tournaments/${detail.data.slug}/print`}>Print view</Link> : undefined}
    >
      {detail.loading || standings.loading ? <div className="card">Loading standings...</div> : null}
      {detail.error || standings.error ? <div className="card error-card">{detail.error ?? standings.error}</div> : null}
      {detail.data ? (
        <>
          <PublicTournamentTabs slug={detail.data.slug} current="standings" showTeams={showTeams} />
        </>
      ) : null}
      {standings.data ? (
        <StandingsTable
          entries={standings.data}
          tournamentStatus={detail.data?.status}
          advancementKind={primaryStage?.advancement_kind}
          advanceCount={primaryStage?.advance_count}
          advancementSummary={primaryStage?.advancement_summary}
          tieBreakRules={primaryStage?.tie_break_rules}
          leaderboardMetric={primaryStage?.leaderboard_metric}
          scoreDirection={primaryStage?.score_direction}
          scoreLabel={primaryStage?.score_label}
        />
      ) : null}
    </PageShell>
  );
}
