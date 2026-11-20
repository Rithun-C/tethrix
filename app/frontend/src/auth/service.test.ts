// The real OidcAuthService, with fetch mocked: proves it reads the backend's settings
// and starts signed out without contacting any sign-in server.

import { OidcAuthService } from "./service";

const CONFIG = {
  authority: "http://localhost:8090/local",
  clientId: "local-app",
  scope: "openid email",
  authorizationEndpoint: "http://localhost:8090/local/authorize",
  tokenEndpoint: "http://localhost:8090/local/token",
  revocationEndpoint: "http://localhost:8090/local/revoke",
  logoutEndpoint: "http://localhost:8090/local/endsession",
};

describe("OidcAuthService", () => {
  beforeEach(() => {
    sessionStorage.clear();
  });

  it("starts signed out when nothing is stored, after one settings request", async () => {
    const fetchMock = vi.fn(() =>
      Promise.resolve(new Response(JSON.stringify(CONFIG), { status: 200 })),
    );
    vi.stubGlobal("fetch", fetchMock);

    const service = new OidcAuthService();

    expect(await service.init()).toBeNull();
    expect(service.accessToken()).toBeUndefined();
    expect(fetchMock).toHaveBeenCalledOnce();
    expect(fetchMock).toHaveBeenCalledWith("/api/v1/auth/config");
  });

  it("restores the session only once, however often it is asked", async () => {
    const fetchMock = vi.fn(() =>
      Promise.resolve(new Response(JSON.stringify(CONFIG), { status: 200 })),
    );
    vi.stubGlobal("fetch", fetchMock);
    const service = new OidcAuthService();

    const [first, second] = await Promise.all([service.init(), service.init()]);

    expect(first).toBeNull();
    expect(second).toBeNull();
    expect(fetchMock).toHaveBeenCalledOnce();
  });

  it("fails when the backend has no sign-in settings", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(() => Promise.resolve(new Response("{}", { status: 503 }))),
    );

    await expect(new OidcAuthService().init()).rejects.toThrow("Sign-in is not available");
  });
});
