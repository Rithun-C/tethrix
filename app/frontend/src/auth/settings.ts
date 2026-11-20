// The sign-in settings: what the backend tells us (GET /api/v1/auth/config, B4
// decision 4) turned into oidc-client-ts settings.
//
// Every endpoint is given explicitly, so the browser never fetches the issuer's
// discovery document: one fewer address for the Content Security Policy to allow.

import { WebStorageStateStore, type UserManagerSettings } from "oidc-client-ts";

import { CALLBACK_PATH } from "./returnTo";
import { SessionUserStore } from "./sessionUserStore";

export interface AuthConfig {
  authority: string;
  clientId: string;
  scope: string;
  authorizationEndpoint: string;
  tokenEndpoint: string;
  revocationEndpoint: string;
  logoutEndpoint: string;
}

const FIELDS = [
  "authority",
  "clientId",
  "scope",
  "authorizationEndpoint",
  "tokenEndpoint",
  "revocationEndpoint",
  "logoutEndpoint",
] as const;

export function isAuthConfig(value: unknown): value is AuthConfig {
  if (typeof value !== "object" || value === null) return false;
  const record = value as Record<string, unknown>;
  return FIELDS.every((field) => typeof record[field] === "string" && record[field] !== "");
}

export function buildSettings(
  config: AuthConfig,
  origin: string,
  storage: Storage,
): UserManagerSettings {
  return {
    authority: config.authority,
    client_id: config.clientId,
    scope: config.scope,
    // Authorization code flow; oidc-client-ts always adds PKCE to it.
    response_type: "code",
    redirect_uri: `${origin}${CALLBACK_PATH}`,
    post_logout_redirect_uri: `${origin}/`,
    metadata: {
      issuer: config.authority,
      authorization_endpoint: config.authorizationEndpoint,
      token_endpoint: config.tokenEndpoint,
      revocation_endpoint: config.revocationEndpoint,
      end_session_endpoint: config.logoutEndpoint,
    },
    // The profile comes from the ID token; no call to a userinfo endpoint.
    loadUserInfo: false,
    // Session monitoring uses a hidden iframe on the sign-in server; our CSP allows no
    // frames, and the refresh token does the job.
    monitorSession: false,
    // Refresh the access token shortly before it expires, with the refresh token.
    automaticSilentRenew: true,
    // On sign-out, revoke the refresh token at the sign-in server (SR-05).
    revokeTokenTypes: ["refresh_token"],
    // Both stores use sessionStorage, never localStorage (SR-53). The state store holds
    // the PKCE verifier between "go to sign-in" and "come back".
    userStore: new SessionUserStore(storage),
    stateStore: new WebStorageStateStore({ store: storage, prefix: "oidc." }),
  };
}
