import type { AuthUser } from "../../api/types";

export const ADMIN_ROLE = "ADMIN";
export const TOURNAMENT_EDITOR_ROLE = "TOURNAMENT_EDITOR";

export function hasAnyRole(user: AuthUser | null, roles: string[]) {
  if (!user) return false;
  return roles.some((role) => user.roles.includes(role));
}

export function canAccessAdmin(user: AuthUser | null) {
  return hasAnyRole(user, [ADMIN_ROLE, TOURNAMENT_EDITOR_ROLE]);
}

export function canManageUsers(user: AuthUser | null) {
  return hasAnyRole(user, [ADMIN_ROLE]);
}

export function canCreateTournament(user: AuthUser | null) {
  return canAccessAdmin(user);
}

export function canDeleteTournament(user: AuthUser | null) {
  return hasAnyRole(user, [ADMIN_ROLE]);
}
