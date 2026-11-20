// A stand-in for the real sign-in service, for tests only (nothing in the app imports it).

import { vi } from "vitest";

import type { AuthService, SessionUser } from "./service";

export const ALICE: SessionUser = { userId: "alice", email: "alice@example.com" };

export class FakeAuth implements AuthService {
  user: SessionUser | null;
  token: string | undefined;
  returnTo = "/";
  private listeners = new Set<() => void>();

  constructor(user: SessionUser | null = ALICE) {
    this.user = user;
    this.token = user ? "test-access-token" : undefined;
  }

  init = vi.fn(() => Promise.resolve(this.user));
  signIn = vi.fn<(returnTo: string) => Promise<void>>(() => Promise.resolve());
  completeSignIn = vi.fn(() => Promise.resolve({ user: ALICE, returnTo: this.returnTo }));
  signOut = vi.fn(() => Promise.resolve());
  forget = vi.fn(() => {
    this.token = undefined;
    return Promise.resolve();
  });

  accessToken(): string | undefined {
    return this.token;
  }

  onSessionEnded(listener: () => void): () => void {
    this.listeners.add(listener);
    return () => this.listeners.delete(listener);
  }

  endSession(): void {
    for (const listener of this.listeners) listener();
  }
}
