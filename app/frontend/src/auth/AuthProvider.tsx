// Holds the sign-in state for the whole app and connects it to the API client.

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";

import { setAuthHooks } from "../api/client";
import { useIdleSignOut } from "./idle";
import { CALLBACK_PATH } from "./returnTo";
import type { AuthService, SessionUser } from "./service";

export type AuthStatus = "loading" | "signedIn" | "signedOut" | "error";

export interface AuthState {
  status: AuthStatus;
  user: SessionUser | null;
  signIn: (returnTo: string) => void;
  signOut: () => void;
  completeSignIn: () => Promise<string>;
}

const AuthContext = createContext<AuthState | null>(null);

export function useAuth(): AuthState {
  const state = useContext(AuthContext);
  if (!state) throw new Error("useAuth must be used inside <AuthProvider>");
  return state;
}

interface Props {
  service: AuthService;
  children: ReactNode;
  idleLimitMs?: number;
}

export function AuthProvider({ service, children, idleLimitMs }: Props) {
  const [status, setStatus] = useState<AuthStatus>("loading");
  const [user, setUser] = useState<SessionUser | null>(null);

  const ended = useCallback(() => {
    setUser(null);
    setStatus("signedOut");
  }, []);

  // Restore a session once at start. The callback page does its own work instead.
  useEffect(() => {
    if (window.location.pathname.startsWith(CALLBACK_PATH)) return;
    let cancelled = false;
    service.init().then(
      (restored) => {
        if (cancelled) return;
        setUser(restored);
        setStatus(restored ? "signedIn" : "signedOut");
      },
      () => {
        if (!cancelled) setStatus("error");
      },
    );
    return () => {
      cancelled = true;
    };
  }, [service]);

  useEffect(() => service.onSessionEnded(ended), [service, ended]);

  // Every API call gets the token; a 401 ends the session in this tab.
  useEffect(() => {
    setAuthHooks({
      accessToken: () => service.accessToken(),
      onUnauthorized: () => {
        void service.forget().then(ended);
      },
    });
    return () => {
      setAuthHooks(undefined);
    };
  }, [service, ended]);

  const signIn = useCallback(
    (returnTo: string) => {
      service.signIn(returnTo).catch(() => {
        setStatus("error");
      });
    },
    [service],
  );

  const signOut = useCallback(() => {
    setUser(null);
    setStatus("signedOut");
    service.signOut().catch(() => {
      // The session is already forgotten locally; nothing else to do.
    });
  }, [service]);

  const completeSignIn = useCallback(async () => {
    const { user: signedIn, returnTo } = await service.completeSignIn();
    setUser(signedIn);
    setStatus("signedIn");
    return returnTo;
  }, [service]);

  useIdleSignOut(status === "signedIn", signOut, idleLimitMs);

  const value = useMemo(
    () => ({ status, user, signIn, signOut, completeSignIn }),
    [status, user, signIn, signOut, completeSignIn],
  );
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
