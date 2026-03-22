export interface AuthUser {
  id: string;
  username: string;
  email: string;
  roles: string[];
}

export interface PlacementPoint {
  placement: number;
  points: number;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
  user: AuthUser;
}

export interface ApiMessage {
  message: string;
}

export interface UserRecord {
  id: string;
  username: string;
  email: string;
  is_active: boolean;
  roles: string[];
}

export interface DirectoryPlayer {
  id: string;
  name: string;
}

export interface DirectoryTeam {
  id: string;
  name: string;
  members: DirectoryPlayer[];
}

export interface TournamentCard {
  id: string;
  name: string;
  slug: string;
  description: string;
  format: string;
  participant_type: string;
  status: string;
  is_public: boolean;
  participant_count: number;
  current_round_name: string | null;
  match_size: number | null;
}

export interface Participant {
  id: string;
  display_name: string;
  kind: string;
  seed_number: number | null;
  members: string[];
}

export interface MatchEntrant {
  participant_id: string;
  display_name: string;
  slot_number: number;
  seed_number: number | null;
  rank: number | null;
  points_awarded: number | null;
  score: number | null;
  tie_group: number | null;
}

export interface MatchRecord {
  id: string;
  name: string;
  sequence: number;
  status: string;
  scheduled_at: string | null;
  notes: string;
  tournament_id: string;
  tournament_name: string;
  tournament_slug: string;
  round_id: string;
  round_name: string;
  is_bye: boolean;
  results_locked: boolean;
  entrants: MatchEntrant[];
}

export interface RoundRecord {
  id: string;
  name: string;
  number: number;
  status: string;
  is_final: boolean;
  bracket_kind: string | null;
  matches: MatchRecord[];
}

export interface StageRecord {
  id: string;
  name: string;
  order_index: number;
  match_size: number | null;
  advancement_kind: string | null;
  advance_count: number | null;
  points_scheme: PlacementPoint[];
  tie_break_rules: string[];
  rounds: RoundRecord[];
  advancement_summary: string | null;
}

export interface StandingEntry {
  participant_id: string;
  display_name: string;
  total_points: number;
  matches_played: number;
  best_rank: number | null;
  average_rank: number | null;
  current_status: string;
  latest_round_name: string | null;
  latest_rank: number | null;
  final_placement: number | null;
}

export interface TournamentDetail {
  id: string;
  name: string;
  slug: string;
  description: string;
  format: string;
  participant_type: string;
  status: string;
  is_public: boolean;
  participants: Participant[];
  stages: StageRecord[];
  standings: StandingEntry[];
  qualified: string[];
  eliminated: string[];
  can_generate_next_round: boolean;
}

export interface DashboardRecord {
  tournament_name: string;
  tournament_slug: string;
  tournament_format: string;
  participant_type: string;
  participant_count: number;
  tournament_status: string;
  current_round_name: string | null;
  rounds: RoundRecord[];
  upcoming_matches: MatchRecord[];
  standings: StandingEntry[];
  qualified: string[];
  eliminated: string[];
  podium: StandingEntry[];
  auto_refresh_seconds: number;
}

export interface AdminDashboardRecord {
  tournaments: number;
  live_tournaments: number;
  users: number;
  completed_matches: number;
}

export interface UserCreatePayload {
  username: string;
  email: string;
  password: string;
  roles: string[];
}

export interface UserPasswordChangePayload {
  password: string;
}

export interface UserRolesUpdatePayload {
  roles: string[];
}

export interface TournamentCreatePayload {
  name: string;
  description: string;
  format: string;
  participant_type: string;
  match_size: number;
  participants: string[];
  directory_player_ids?: string[];
  directory_team_ids?: string[];
  points_scheme: PlacementPoint[];
  advance_count?: number;
  is_public: boolean;
}

export interface TournamentUpdatePayload {
  name?: string;
  description?: string;
  status?: string;
  is_public?: boolean;
}

export interface MatchResultPayload {
  results: Array<{
    participant_id: string;
    rank: number;
    score?: number;
    tie_group?: number;
    notes?: string;
  }>;
}

export interface TieBreakRuleRecord {
  id: string;
  name: string;
  order_index: number;
  config: {
    rule_type: string;
  };
}

export interface TournamentConfigParticipant {
  name: string;
  members: string[];
}

export interface TournamentConfigExport {
  name: string;
  description: string;
  format: string;
  participant_type: string;
  match_size: number;
  advance_count?: number | null;
  is_public: boolean;
  points_scheme: PlacementPoint[];
  tie_break_rules: TieBreakRuleRecord[];
  participants: TournamentConfigParticipant[];
}

export interface PublicTeam {
  id: string;
  name: string;
  members: string[];
}

export interface PublicTeamsResponse {
  tournament_id: string;
  tournament_name: string;
  participant_type: string;
  teams: PublicTeam[];
}

export interface ParticipantImportResult {
  imported: number;
  skipped: number;
  errors: string[];
}
