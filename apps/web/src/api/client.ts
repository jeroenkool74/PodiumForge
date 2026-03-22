import type {
  ApiMessage,
  AdminDashboardRecord,
  DashboardRecord,
  DirectoryPlayer,
  DirectoryTeam,
  MatchRecord,
  MatchResultPayload,
  PlacementPoint,
  PublicTeamsResponse,
  RoundRecord,
  StandingEntry,
  TieBreakRuleRecord,
  TokenResponse,
  TournamentCard,
  TournamentCreatePayload,
  TournamentDetail,
  TournamentUpdatePayload,
  UserCreatePayload,
  UserPasswordChangePayload,
  UserRecord,
  UserRolesUpdatePayload,
} from "./types";

const API_BASE = import.meta.env.VITE_API_BASE ?? "/api/v1";

function formatFieldLabel(path: Array<string | number>) {
  const relevant = path.filter((segment) => segment !== "body");
  if (!relevant.length) return "Field";
  return relevant
    .map((segment) => `${segment}`)
    .join(" ")
    .replace(/_/g, " ")
    .replace(/\b\w/g, (character) => character.toUpperCase());
}

function formatApiError(detail: unknown): string {
  if (typeof detail === "string" && detail.trim()) {
    return detail;
  }

  if (Array.isArray(detail)) {
    const messages = detail
      .map((item) => {
        if (typeof item === "string") {
          return item;
        }

        if (item && typeof item === "object") {
          const candidate = item as { loc?: Array<string | number>; msg?: string };
          if (candidate.msg) {
            const label = formatFieldLabel(candidate.loc ?? []);
            return `${label}: ${candidate.msg}`;
          }
        }

        return null;
      })
      .filter((message): message is string => Boolean(message));

    if (messages.length) {
      return messages.join(" ");
    }
  }

  if (detail && typeof detail === "object") {
    const candidate = detail as { message?: string };
    if (candidate.message) {
      return candidate.message;
    }
  }

  return "Request failed";
}

async function request<T>(path: string, init: RequestInit = {}, token?: string): Promise<T> {
  const headers = new Headers(init.headers);
  if (init.body && !(init.body instanceof FormData) && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }
  if (token) {
    headers.set("Authorization", `Bearer ${token}`);
  }

  const response = await fetch(`${API_BASE}${path}`, {
    ...init,
    cache: init.cache ?? "no-store",
    headers,
  });

  if (!response.ok) {
    let message = "Request failed";
    try {
      const errorBody = await response.json();
      message = formatApiError(errorBody.detail ?? errorBody.message ?? errorBody);
    } catch {
      message = response.statusText || message;
    }
    throw new Error(message);
  }

  if (response.status === 204) {
    return undefined as T;
  }

  const contentType = response.headers.get("content-type") ?? "";
  if (!contentType.includes("application/json")) {
    return undefined as T;
  }

  return response.json() as Promise<T>;
}

export const api = {
  login: (login: string, password: string) =>
    request<TokenResponse>("/auth/login", {
      method: "POST",
      body: JSON.stringify({ login, password }),
    }),
  me: (token: string) => request<TokenResponse["user"]>("/auth/me", {}, token),
  requestPasswordReset: (email: string) =>
    request<ApiMessage>("/auth/password-reset/request", {
      method: "POST",
      body: JSON.stringify({ email }),
    }),
  confirmPasswordReset: (token: string, password: string) =>
    request<ApiMessage>("/auth/password-reset/confirm", {
      method: "POST",
      body: JSON.stringify({ token, password }),
    }),

  listPublicTournaments: () => request<TournamentCard[]>("/public/tournaments"),
  getPublicTournament: (slug: string) => request<TournamentDetail>(`/public/tournaments/${slug}`),
  getPublicStandings: (slug: string) => request<StandingEntry[]>(`/public/tournaments/${slug}/standings`),
  getPublicRound: (slug: string, roundId: string) => request<RoundRecord>(`/public/tournaments/${slug}/rounds/${roundId}`),
  getPublicMatch: (matchId: string) => request<MatchRecord>(`/public/matches/${matchId}`),
  getPublicTeams: (slug: string) => request<PublicTeamsResponse>(`/public/tournaments/${slug}/teams`),
  getDashboard: (slug: string) => request<DashboardRecord>(`/public/tournaments/${slug}/dashboard`),

  getAdminDashboard: (token: string) => request<AdminDashboardRecord>("/tournaments/dashboard", {}, token),
  listManagedTournaments: (token: string) => request<TournamentCard[]>("/tournaments", {}, token),
  getManagedTournament: (token: string, tournamentId: string) => request<TournamentDetail>(`/tournaments/${tournamentId}`, {}, token),
  createTournament: (token: string, payload: TournamentCreatePayload) =>
    request<TournamentDetail>("/tournaments", { method: "POST", body: JSON.stringify(payload) }, token),
  updateTournament: (token: string, tournamentId: string, payload: TournamentUpdatePayload) =>
    request<TournamentDetail>(`/tournaments/${tournamentId}`, { method: "PATCH", body: JSON.stringify(payload) }, token),
  updatePointsScheme: (token: string, tournamentId: string, pointsScheme: PlacementPoint[]) =>
    request<TournamentDetail>(`/tournaments/${tournamentId}/points-scheme`, { method: "PATCH", body: JSON.stringify({ points_scheme: pointsScheme }) }, token),
  recalculatePoints: (token: string, tournamentId: string) =>
    request<{ recalculated: number; total_results: number; message: string }>(`/tournaments/${tournamentId}/recalculate-points`, { method: "POST" }, token),
  deleteTournament: (token: string, tournamentId: string) =>
    request<void>(`/tournaments/${tournamentId}`, { method: "DELETE" }, token),
  generateNextRound: (token: string, tournamentId: string) =>
    request<RoundRecord>(`/tournaments/${tournamentId}/rounds/next`, { method: "POST" }, token),
  addParticipant: (token: string, tournamentId: string, payload: { display_name: string; directory_entry_id?: string; seed_number?: number; team_members?: string[] }) =>
    request<TournamentDetail["participants"][number]>(`/tournaments/${tournamentId}/participants`, { method: "POST", body: JSON.stringify(payload) }, token),
  getTieBreakRules: (token: string, tournamentId: string) => request<TieBreakRuleRecord[]>(`/tournaments/${tournamentId}/tie-break-rules`, {}, token),
  createTieBreakRule: (token: string, tournamentId: string, payload: Omit<TieBreakRuleRecord, "id">) =>
    request<TieBreakRuleRecord>(`/tournaments/${tournamentId}/tie-break-rules`, { method: "POST", body: JSON.stringify(payload) }, token),
  updateTieBreakRule: (token: string, tournamentId: string, ruleId: string, payload: Partial<Omit<TieBreakRuleRecord, "id">>) =>
    request<TieBreakRuleRecord>(`/tournaments/${tournamentId}/tie-break-rules/${ruleId}`, { method: "PATCH", body: JSON.stringify(payload) }, token),
  deleteTieBreakRule: (token: string, tournamentId: string, ruleId: string) =>
    request<{ deleted: boolean; rule_id: string }>(`/tournaments/${tournamentId}/tie-break-rules/${ruleId}`, { method: "DELETE" }, token),

  listDirectoryPlayers: (token: string) => request<DirectoryPlayer[]>("/directory/players", {}, token),
  createDirectoryPlayer: (token: string, payload: { name: string }) => request<DirectoryPlayer>("/directory/players", { method: "POST", body: JSON.stringify(payload) }, token),
  updateDirectoryPlayer: (token: string, playerId: string, payload: { name: string }) => request<DirectoryPlayer>(`/directory/players/${playerId}`, { method: "PUT", body: JSON.stringify(payload) }, token),
  deleteDirectoryPlayer: (token: string, playerId: string) => request<{ deleted: boolean; player_id: string }>(`/directory/players/${playerId}`, { method: "DELETE" }, token),
  listDirectoryTeams: (token: string) => request<DirectoryTeam[]>("/directory/teams", {}, token),
  createDirectoryTeam: (token: string, payload: { name: string; player_ids: string[] }) => request<DirectoryTeam>("/directory/teams", { method: "POST", body: JSON.stringify(payload) }, token),
  updateDirectoryTeam: (token: string, teamId: string, payload: { name: string; player_ids: string[] }) => request<DirectoryTeam>(`/directory/teams/${teamId}`, { method: "PUT", body: JSON.stringify(payload) }, token),
  deleteDirectoryTeam: (token: string, teamId: string) => request<{ deleted: boolean; team_id: string }>(`/directory/teams/${teamId}`, { method: "DELETE" }, token),

  listUsers: (token: string) => request<UserRecord[]>("/users", {}, token),
  createUser: (token: string, payload: UserCreatePayload) =>
    request<UserRecord>("/users", { method: "POST", body: JSON.stringify(payload) }, token),
  updateUserRoles: (token: string, userId: string, payload: UserRolesUpdatePayload) =>
    request<UserRecord>(`/users/${userId}/roles`, { method: "PUT", body: JSON.stringify(payload) }, token),
  changeUserPassword: (token: string, userId: string, payload: UserPasswordChangePayload) =>
    request<void>(`/users/${userId}/password`, { method: "POST", body: JSON.stringify(payload) }, token),
  deleteUser: (token: string, userId: string) =>
    request<void>(`/users/${userId}`, { method: "DELETE" }, token),

  getManagedMatch: (token: string, matchId: string) => request<MatchRecord>(`/matches/${matchId}`, {}, token),
  saveMatchResults: (token: string, matchId: string, payload: MatchResultPayload) =>
    request<MatchRecord>(`/matches/${matchId}/results`, { method: "POST", body: JSON.stringify(payload) }, token),
  clearMatchResults: (token: string, matchId: string) => request<MatchRecord>(`/matches/${matchId}/results`, { method: "DELETE" }, token),

  getProtectedStandings: (token: string, tournamentId: string) => request<StandingEntry[]>(`/standings/tournaments/${tournamentId}`, {}, token),
};
