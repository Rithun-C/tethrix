import { useEffect } from "react";
import { Outlet, useLocation } from "react-router";

import { useAuth } from "../auth/AuthProvider";

/** Shows the pages inside it only to a signed-in user; anyone else goes to sign-in. */
export function RequireAuth() {
  const { status, signIn } = useAuth();
  const location = useLocation();
  const here = `${location.pathname}${location.search}`;

  useEffect(() => {
    if (status === "signedOut") signIn(here);
  }, [status, signIn, here]);

  if (status === "signedIn") return <Outlet />;
  if (status === "error") {
    return (
      <main className="content">
        <h1>Sign-in is not available</h1>
        <p>The sign-in service could not be reached. Try again in a moment.</p>
        <button
          type="button"
          onClick={() => {
            signIn(here);
          }}
        >
          Try again
        </button>
      </main>
    );
  }
  return (
    <main className="content">
      <p role="status">{status === "loading" ? "Loading..." : "Going to the sign-in page..."}</p>
    </main>
  );
}
