/**
 * Token + user storage. Uses localStorage (acceptable for this beta;
 * a future iteration could move to httpOnly cookies for stronger XSS
 * protection). All access is guarded with `typeof window` checks so
 * this module is safe to import from server components too.
 */
export type Role = "admin" | "gatekeeper";

export interface AuthUser {
  id: string;
  tenant_id?: string | null;
  name: string;
  mobile: string;
  email?: string | null;
  role: Role;
  is_active: boolean;
  is_root: boolean;
}

const ACCESS_KEY = "truckpark_access_token";
const REFRESH_KEY = "truckpark_refresh_token";
const USER_KEY = "truckpark_user";

export function setTokens(accessToken: string, refreshToken: string, user: AuthUser) {
  if (typeof window === "undefined") return;
  localStorage.setItem(ACCESS_KEY, accessToken);
  localStorage.setItem(REFRESH_KEY, refreshToken);
  localStorage.setItem(USER_KEY, JSON.stringify(user));
}

export function getAccessToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(ACCESS_KEY);
}

export function getRefreshToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(REFRESH_KEY);
}

export function getStoredUser(): AuthUser | null {
  if (typeof window === "undefined") return null;
  const raw = localStorage.getItem(USER_KEY);
  if (!raw) return null;
  try {
    return JSON.parse(raw) as AuthUser;
  } catch {
    return null;
  }
}

export function clearTokens() {
  if (typeof window === "undefined") return;
  localStorage.removeItem(ACCESS_KEY);
  localStorage.removeItem(REFRESH_KEY);
  localStorage.removeItem(USER_KEY);
}

export function isAuthenticated(): boolean {
  return !!getAccessToken();
}

export function homeRouteForRole(role: Role): string {
  return role === "admin" ? "/dashboard" : "/entry";
}
