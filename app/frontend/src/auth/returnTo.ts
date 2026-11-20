// Where to go after sign-in (T-039).
//
// The sign-in flow carries "the page you wanted" through Cognito and back. Anything
// that comes back is treated as untrusted: only a path on our own site is followed.
// "//evil.example" and "/\evil.example" look like paths but browsers treat them as
// another site, so they are refused too.

export const CALLBACK_PATH = "/auth/callback";

export function safeReturnTo(value: unknown): string {
  if (typeof value !== "string") return "/";
  if (!value.startsWith("/") || value.startsWith("//") || value.startsWith("/\\")) return "/";
  if (value.startsWith(CALLBACK_PATH)) return "/";
  // Control characters (tabs, line breaks) can also bend how a browser reads a URL.
  // eslint-disable-next-line no-control-regex
  if (/[\u0000-\u001f]/.test(value)) return "/";
  return value;
}
