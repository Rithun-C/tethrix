import { WebStorageStateStore } from "oidc-client-ts";

import { buildSettings, isAuthConfig, type AuthConfig } from "./settings";
import { SessionUserStore } from "./sessionUserStore";

const COGNITO = "https://tethrix-app.auth.us-east-1.amazoncognito.com";
const CONFIG: AuthConfig = {
  authority: "https://cognito-idp.us-east-1.amazonaws.com/us-east-1_AbCdEf123",
  clientId: "abc123def456",
  scope: "openid email",
  authorizationEndpoint: `${COGNITO}/oauth2/authorize`,
  tokenEndpoint: `${COGNITO}/oauth2/token`,
  revocationEndpoint: `${COGNITO}/oauth2/revoke`,
  logoutEndpoint: `${COGNITO}/logout`,
};

describe("buildSettings", () => {
  const settings = buildSettings(CONFIG, "https://tethrix.satrix.in", sessionStorage);

  it("uses the code flow with our callback and sign-out addresses", () => {
    expect(settings.response_type).toBe("code");
    expect(settings.client_id).toBe("abc123def456");
    expect(settings.redirect_uri).toBe("https://tethrix.satrix.in/auth/callback");
    expect(settings.post_logout_redirect_uri).toBe("https://tethrix.satrix.in/");
  });

  it("gives every endpoint, so no discovery request is made", () => {
    expect(settings.metadata).toEqual({
      issuer: CONFIG.authority,
      authorization_endpoint: CONFIG.authorizationEndpoint,
      token_endpoint: CONFIG.tokenEndpoint,
      revocation_endpoint: CONFIG.revocationEndpoint,
      end_session_endpoint: CONFIG.logoutEndpoint,
    });
  });

  it("keeps tokens out of localStorage and uses no iframes", () => {
    expect(settings.userStore).toBeInstanceOf(SessionUserStore);
    expect(settings.stateStore).toBeInstanceOf(WebStorageStateStore);
    expect(settings.monitorSession).toBe(false);
    expect(settings.loadUserInfo).toBe(false);
  });

  it("revokes the refresh token on sign-out (SR-05)", () => {
    expect(settings.revokeTokenTypes).toEqual(["refresh_token"]);
    expect(settings.automaticSilentRenew).toBe(true);
  });
});

describe("isAuthConfig", () => {
  it("accepts the backend's answer", () => {
    expect(isAuthConfig(CONFIG)).toBe(true);
  });

  it.each([null, {}, { ...CONFIG, clientId: "" }, { ...CONFIG, tokenEndpoint: 5 }])(
    "refuses %j",
    (value) => {
      expect(isAuthConfig(value)).toBe(false);
    },
  );
});
