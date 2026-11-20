import { SessionUserStore, withoutTokens } from "./sessionUserStore";

const USER = JSON.stringify({
  access_token: "secret-access",
  id_token: "secret-id",
  refresh_token: "refresh",
  expires_at: 9999999999,
  profile: { sub: "alice" },
});

describe("SessionUserStore (SR-53)", () => {
  beforeEach(() => {
    sessionStorage.clear();
    localStorage.clear();
  });

  it("keeps the full user in memory", async () => {
    const store = new SessionUserStore(sessionStorage);
    await store.set("user:x", USER);

    expect(await store.get("user:x")).toBe(USER);
  });

  it("never writes the access token or ID token to storage", async () => {
    const store = new SessionUserStore(sessionStorage);
    await store.set("user:x", USER);

    const stored = sessionStorage.getItem("user:x") ?? "";
    expect(stored).not.toContain("secret-access");
    expect(stored).not.toContain("secret-id");
    expect(JSON.parse(stored)).toMatchObject({ refresh_token: "refresh", expires_at: 0 });
  });

  it("after a reload has only the stored copy, marked expired", async () => {
    await new SessionUserStore(sessionStorage).set("user:x", USER);
    const afterReload = new SessionUserStore(sessionStorage);

    const user = JSON.parse((await afterReload.get("user:x")) ?? "{}") as Record<string, unknown>;
    expect(user.access_token).toBeUndefined();
    expect(user.expires_at).toBe(0);
  });

  it("removes from memory and storage", async () => {
    const store = new SessionUserStore(sessionStorage);
    await store.set("user:x", USER);
    await store.remove("user:x");

    expect(await store.get("user:x")).toBeNull();
    expect(sessionStorage.length).toBe(0);
  });

  it("never touches localStorage", async () => {
    const store = new SessionUserStore(sessionStorage);
    await store.set("user:x", USER);

    expect(localStorage.length).toBe(0);
  });

  it("stores nothing it cannot read", () => {
    expect(withoutTokens("not json")).toBe("{}");
  });
});
