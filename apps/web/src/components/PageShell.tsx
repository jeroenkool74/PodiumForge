import { NavLink } from "react-router-dom";
import { useAuth } from "../features/auth/AuthContext";
import { canAccessAdmin, canCreateTournament, canManageUsers } from "../features/auth/permissions";

interface PageShellProps {
  mode: "public" | "admin";
  title: string;
  subtitle?: string;
  actions?: React.ReactNode;
  immersive?: boolean;
  children: React.ReactNode;
}

export function PageShell({ mode, title, subtitle, actions, immersive = false, children }: PageShellProps) {
  const { isAuthenticated, logout, user } = useAuth();
  const showAdminLink = isAuthenticated && canAccessAdmin(user);
  const showUsersLink = canManageUsers(user);
  const showNewTournamentLink = canCreateTournament(user);
  const showDirectoryLinks = showAdminLink;
  const heroKicker = mode === "public"
    ? "Live standings, match results, and tournament dashboards"
    : "Tournament operations for local events";

  return (
    <div className={`app-shell ${mode === "admin" ? "admin-shell" : "public-shell"} ${immersive ? "immersive-shell" : ""}`}>
      <header className={`hero-bar ${immersive ? "immersive-hero-bar" : ""}`}>
        <div>
          <NavLink to="/" className="brand-mark">
            PodiumForge
          </NavLink>
          {!immersive ? <p className="hero-kicker">{heroKicker}</p> : null}
          <h1>{title}</h1>
          {subtitle ? <p className="hero-subtitle">{subtitle}</p> : null}
        </div>
        <div className="hero-actions">
          {mode === "public" && !immersive ? (
            <nav className="nav-cluster">
              <NavLink to="/">Home</NavLink>
              {showAdminLink ? <NavLink to="/admin">Admin</NavLink> : <NavLink to="/login">Login</NavLink>}
            </nav>
          ) : mode === "admin" ? (
            <>
              <nav className="nav-cluster">
                <NavLink to="/admin">Dashboard</NavLink>
                {showUsersLink ? <NavLink to="/admin/users">Users</NavLink> : null}
                {showDirectoryLinks ? <NavLink to="/admin/players">Players</NavLink> : null}
                {showDirectoryLinks ? <NavLink to="/admin/teams">Teams</NavLink> : null}
                {showNewTournamentLink ? <NavLink to="/admin/tournaments/new">New Tournament</NavLink> : null}
              </nav>
              <div className="admin-user-chip">
                <span>{user?.username}</span>
                <button type="button" className="ghost-button" onClick={logout}>
                  Logout
                </button>
              </div>
            </>
          ) : null}
          {actions}
        </div>
      </header>
      <main className="page-grid">{children}</main>
    </div>
  );
}
