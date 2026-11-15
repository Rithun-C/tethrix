// Runs before every test file.

import "@testing-library/jest-dom/vitest";
import { cleanup } from "@testing-library/react";
import { afterEach, beforeEach, vi } from "vitest";

// A test that forgets to replace fetch must fail loudly, not call a real server.
beforeEach(() => {
  vi.stubGlobal(
    "fetch",
    vi.fn(() => Promise.reject(new Error("fetch was called without a mock"))),
  );
});

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});
