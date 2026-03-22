import { Navigate, Route, Routes, useParams } from "react-router-dom";
import { ProtectedRoute } from "../features/auth/ProtectedRoute";
import { AdminHomePage } from "../features/admin/pages/AdminHomePage";
import { LoginPage } from "../features/admin/pages/LoginPage";
import { MatchResultEntryPage } from "../features/admin/pages/MatchResultEntryPage";
import { PasswordResetPage } from "../features/admin/pages/PasswordResetPage";
import { PlayersDirectoryPage } from "../features/admin/pages/PlayersDirectoryPage";
import { TeamsDirectoryPage } from "../features/admin/pages/TeamsDirectoryPage";
import { TournamentCreatePage } from "../features/admin/pages/TournamentCreatePage";
import { TournamentEditPage } from "../features/admin/pages/TournamentEditPage";
import { UserManagementPage } from "../features/admin/pages/UserManagementPage";
import { ADMIN_ROLE, TOURNAMENT_EDITOR_ROLE } from "../features/auth/permissions";
import { NotFoundPage } from "../features/public/pages/NotFoundPage";
import { HomePage } from "../features/public/pages/HomePage";
import { MatchDetailPage } from "../features/public/pages/MatchDetailPage";
import { PrintStandingsPage } from "../features/public/pages/PrintStandingsPage";
import { PublicDashboardPage } from "../features/public/pages/PublicDashboardPage";
import { PublicTeamsPage } from "../features/public/pages/PublicTeamsPage";
import { RoundDetailPage } from "../features/public/pages/RoundDetailPage";
import { StandingsPage } from "../features/public/pages/StandingsPage";
import { TournamentOverviewPage } from "../features/public/pages/TournamentOverviewPage";

function LegacyDashboardRedirect() {
  const { slug } = useParams();
  return <Navigate to={slug ? `/tournaments/${slug}` : "/"} replace />;
}

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<HomePage />} />
      <Route path="/tournaments/:slug" element={<TournamentOverviewPage />} />
      <Route path="/tournaments/:slug/standings" element={<StandingsPage />} />
      <Route path="/tournaments/:slug/print" element={<PrintStandingsPage />} />
      <Route path="/tournaments/:slug/teams" element={<PublicTeamsPage />} />
      <Route path="/tournaments/:slug/rounds/:roundId" element={<RoundDetailPage />} />
      <Route path="/matches/:matchId" element={<MatchDetailPage />} />
      <Route path="/dashboard/:slug/tv" element={<PublicDashboardPage immersive />} />
      <Route path="/dashboard/:slug" element={<LegacyDashboardRedirect />} />
      <Route path="/login" element={<LoginPage />} />
      <Route path="/reset-password" element={<PasswordResetPage />} />
      <Route path="/admin" element={<ProtectedRoute roles={[ADMIN_ROLE, TOURNAMENT_EDITOR_ROLE]}><AdminHomePage /></ProtectedRoute>} />
      <Route path="/admin/users" element={<ProtectedRoute roles={[ADMIN_ROLE]} fallbackTo="/admin"><UserManagementPage /></ProtectedRoute>} />
      <Route path="/admin/players" element={<ProtectedRoute roles={[ADMIN_ROLE, TOURNAMENT_EDITOR_ROLE]}><PlayersDirectoryPage /></ProtectedRoute>} />
      <Route path="/admin/teams" element={<ProtectedRoute roles={[ADMIN_ROLE, TOURNAMENT_EDITOR_ROLE]}><TeamsDirectoryPage /></ProtectedRoute>} />
      <Route path="/admin/tournaments/new" element={<ProtectedRoute roles={[ADMIN_ROLE, TOURNAMENT_EDITOR_ROLE]}><TournamentCreatePage /></ProtectedRoute>} />
      <Route path="/admin/tournaments/:tournamentId" element={<ProtectedRoute roles={[ADMIN_ROLE, TOURNAMENT_EDITOR_ROLE]}><TournamentEditPage /></ProtectedRoute>} />
      <Route path="/admin/matches/:matchId/entry" element={<ProtectedRoute roles={[ADMIN_ROLE, TOURNAMENT_EDITOR_ROLE]}><MatchResultEntryPage /></ProtectedRoute>} />
      <Route path="*" element={<NotFoundPage />} />
    </Routes>
  );
}
