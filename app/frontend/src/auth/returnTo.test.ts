import { safeReturnTo } from "./returnTo";

describe("safeReturnTo (T-039)", () => {
  it.each(["/", "/todos", "/journal/2026-11-20?tab=1", "/pages/abc#top"])(
    "keeps our own path %s",
    (path) => {
      expect(safeReturnTo(path)).toBe(path);
    },
  );

  it.each([
    "https://evil.example/",
    "//evil.example/",
    "/\\evil.example/",
    "javascript:alert(1)",
    "todos",
    "/auth/callback?code=x",
    "/\tevil",
    "",
  ])("refuses %s", (value) => {
    expect(safeReturnTo(value)).toBe("/");
  });

  it.each([undefined, null, 42, { path: "/todos" }])("refuses a non-string (%s)", (value) => {
    expect(safeReturnTo(value)).toBe("/");
  });
});
