import { useEffect, useRef, useState } from "react";
import { Link, useNavigate } from "react-router";

import { useAuth } from "../auth/AuthProvider";

/**
 * Where the sign-in server sends the browser back to, with a one-time code. The code is
 * swapped for tokens (with the PKCE verifier kept in sessionStorage), then the app
 * goes to the page the user wanted.
 */
export function CallbackPage() {
  const { completeSignIn } = useAuth();
  const navigate = useNavigate();
  const [failed, setFailed] = useState(false);
  // React's StrictMode runs effects twice in development; a code can be used only once.
  const started = useRef(false);

  useEffect(() => {
    if (started.current) return;
    started.current = true;
    completeSignIn().then(
      (returnTo) => {
        void navigate(returnTo, { replace: true });
      },
      () => {
        setFailed(true);
      },
    );
  }, [completeSignIn, navigate]);

  if (failed) {
    return (
      <main className="content">
        <h1>Sign-in did not finish</h1>
        <p>The sign-in link may be old or already used.</p>
        <Link to="/">Sign in again</Link>
      </main>
    );
  }
  return (
    <main className="content">
      <p role="status">Signing in...</p>
    </main>
  );
}
