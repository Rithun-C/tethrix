// What the app needs from sign-in, and the real implementation with oidc-client-ts.
//
// The React code only sees the AuthService interface, so tests use a fake and never
// talk to a sign-in server.

import { UserManager, type User } from "oidc-client-ts";

import { API_PREFIX } from "../api/client";
import { safeReturnTo } from "./returnTo";
import { buildSettings, isAuthConfig } from "./settings";

export interface SessionUser {
  userId: string;
  email: string | undefined;
}

export interface AuthService {
  /** Restores a session (refreshing if needed); null if nobody is signed in. */
  init(): Promise<SessionUser | null>;
  /** Sends the browser to the sign-in page. `returnTo` is where to come back to. */
  signIn(returnTo: string): Promise<void>;
  /** Finishes sign-in on the callback page. */
  completeSignIn(): Promise<{ user: SessionUser; returnTo: string }>;
  /** Revokes the refresh token, forgets the session, and signs out at the sign-in server. */
  signOut(): Promise<void>;
  /** Forgets the session in this tab only (used when the API says 401). */
  forget(): Promise<void>;
  /** The current access token, from memory. */
  accessToken(): string | undefined;
  /** Called when the session ends by itself (expired, refresh failed). */
  onSessionEnded(listener: () => void): () => void;
}

function toSessionUser(user: User): SessionUser {
  const email = user.profile.email;
  return { userId: user.profile.sub, email: typeof email === "string" ? email : undefined };
}

export class OidcAuthService implements AuthService {
  private manager: UserManager | undefined;
  private user: User | null = null;
  private restoring: Promise<SessionUser | null> | undefined;
  private readonly listeners = new Set<() => void>();

  private async getManager(): Promise<UserManager> {
    if (this.manager) return this.manager;
    const response = await fetch(`${API_PREFIX}/auth/config`);
    const config: unknown = response.ok ? await response.json() : undefined;
    if (!isAuthConfig(config)) throw new Error("Sign-in is not available right now.");

    const manager = new UserManager(
      buildSettings(config, window.location.origin, window.sessionStorage),
    );
    manager.events.addUserLoaded((user) => {
      this.user = user;
    });
    const ended = () => {
      this.user = null;
      for (const listener of this.listeners) listener();
    };
    manager.events.addAccessTokenExpired(ended);
    manager.events.addSilentRenewError(ended);
    this.manager = manager;
    return manager;
  }

  init(): Promise<SessionUser | null> {
    // Runs once, however often it is asked: React's StrictMode starts components twice
    // in development, and two refreshes with the same refresh token would race (and
    // would fail outright if refresh-token rotation were ever switched on).
    this.restoring ??= this.restore();
    return this.restoring;
  }

  private async restore(): Promise<SessionUser | null> {
    const manager = await this.getManager();
    const stored = await manager.getUser();
    if (stored && !stored.expired && stored.access_token) {
      this.user = stored;
      return toSessionUser(stored);
    }
    if (stored?.refresh_token) {
      // After a reload: the access token was never stored, so get a new one.
      try {
        const refreshed = await manager.signinSilent();
        if (refreshed) {
          this.user = refreshed;
          return toSessionUser(refreshed);
        }
      } catch {
        // The refresh token expired (12 hours) or was revoked: sign in again.
      }
    }
    await manager.removeUser();
    return null;
  }

  async signIn(returnTo: string): Promise<void> {
    const manager = await this.getManager();
    await manager.signinRedirect({ state: { returnTo: safeReturnTo(returnTo) } });
  }

  async completeSignIn(): Promise<{ user: SessionUser; returnTo: string }> {
    const manager = await this.getManager();
    const user = await manager.signinRedirectCallback();
    this.user = user;
    const state = user.state as { returnTo?: unknown } | undefined;
    return { user: toSessionUser(user), returnTo: safeReturnTo(state?.returnTo) };
  }

  async signOut(): Promise<void> {
    const manager = await this.getManager();
    try {
      await manager.revokeTokens(["refresh_token"]);
    } catch {
      // Revoking can fail if the token already expired; sign-out continues.
    }
    this.user = null;
    await manager.removeUser();
    const home = `${window.location.origin}/`;
    // Cognito's /logout reads `logout_uri`; the local server reads the standard
    // `post_logout_redirect_uri`. Both are sent.
    await manager.signoutRedirect({ extraQueryParams: { logout_uri: home } });
  }

  async forget(): Promise<void> {
    this.user = null;
    if (this.manager) await this.manager.removeUser();
  }

  accessToken(): string | undefined {
    return this.user?.access_token;
  }

  onSessionEnded(listener: () => void): () => void {
    this.listeners.add(listener);
    return () => this.listeners.delete(listener);
  }
}
