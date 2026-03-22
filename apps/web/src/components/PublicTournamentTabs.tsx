import { Link } from "react-router-dom";

type TournamentTab = "overview" | "rounds" | "standings" | "dashboard" | "teams";

function tabClassName(current: TournamentTab, tab: TournamentTab) {
  return `tournament-tab-link ${current === tab ? "active-tournament-tab" : ""}`;
}

export function PublicTournamentTabs({ slug, current, showTeams = false }: { slug: string; current: TournamentTab; showTeams?: boolean }) {
  return (
    <nav className="tournament-tab-row" aria-label="Tournament sections">
      <Link className={tabClassName(current, "overview")} to={`/tournaments/${slug}`}>
        Overview
      </Link>
      <Link className={tabClassName(current, "rounds")} to={`/tournaments/${slug}?tab=rounds`}>
        Rounds
      </Link>
      <Link className={tabClassName(current, "standings")} to={`/tournaments/${slug}/standings`}>
        Standings
      </Link>
      <Link className={tabClassName(current, "dashboard")} to={`/dashboard/${slug}`}>
        Dashboard
      </Link>
      {showTeams ? (
        <Link className={tabClassName(current, "teams")} to={`/tournaments/${slug}/teams`}>
          Teams
        </Link>
      ) : null}
    </nav>
  );
}
