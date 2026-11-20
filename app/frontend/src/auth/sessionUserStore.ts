// Where oidc-client-ts keeps the signed-in user (ADR-0003 decision 6, SR-53).
//
// - The full user, with the access token, lives in memory only. A script injected
//   through an XSS bug cannot read it out of storage.
// - The tab's sessionStorage keeps a copy without the access token and the ID token,
//   so a reload can use the refresh token to get a new access token. sessionStorage is
//   emptied when the tab closes; localStorage is never used.
// - The stored copy is marked as expired, so after a reload the app always refreshes
//   instead of trusting a token it no longer has.

import type { StateStore } from "oidc-client-ts";

const REMOVED: readonly string[] = ["access_token", "id_token"];

export function withoutTokens(json: string): string {
  try {
    const data = JSON.parse(json) as Record<string, unknown>;
    const kept = Object.entries(data).filter(([name]) => !REMOVED.includes(name));
    return JSON.stringify({ ...Object.fromEntries(kept), expires_at: 0 });
  } catch {
    // Not a user record: store nothing rather than something unknown.
    return "{}";
  }
}

export class SessionUserStore implements StateStore {
  private readonly memory = new Map<string, string>();
  private readonly storage: Storage;

  constructor(storage: Storage) {
    this.storage = storage;
  }

  set(key: string, value: string): Promise<void> {
    this.memory.set(key, value);
    this.storage.setItem(key, withoutTokens(value));
    return Promise.resolve();
  }

  get(key: string): Promise<string | null> {
    return Promise.resolve(this.memory.get(key) ?? this.storage.getItem(key));
  }

  remove(key: string): Promise<string | null> {
    const previous = this.memory.get(key) ?? this.storage.getItem(key);
    this.memory.delete(key);
    this.storage.removeItem(key);
    return Promise.resolve(previous);
  }

  getAllKeys(): Promise<string[]> {
    const keys = new Set(this.memory.keys());
    for (let i = 0; i < this.storage.length; i++) {
      const key = this.storage.key(i);
      if (key !== null) keys.add(key);
    }
    return Promise.resolve([...keys]);
  }
}
