/// <reference types="vitest/config" />
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

// Note: Vite is always started with `--configLoader runner` (see the Dockerfile and the
// Makefile). The default loader writes a temporary file next to node_modules, which
// fails in our containers because their file system is read-only.

// Where the dev server sends /api requests. In Docker Compose this is the backend
// container. It only matters for `vite` (the dev server), never for the built site.
const apiTarget = process.env.API_PROXY_TARGET ?? "http://localhost:8080";

export default defineConfig({
  plugins: [react()],

  // Vite's own cache. /tmp is the only writable place in the container.
  cacheDir: "/tmp/vite",

  server: {
    port: 5173,
    strictPort: true,
    // The proxy gives the laptop the same shape as AWS: the browser talks to one
    // address for pages and for /api (in AWS that address is CloudFront). Because the
    // browser never calls a second address, the app needs no CORS settings.
    proxy: {
      "/api": { target: apiTarget, changeOrigin: false },
    },
  },

  build: {
    // Source maps would publish our original source next to the built files.
    sourcemap: false,
  },

  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: ["./src/test-setup.ts"],
    // Vitest's cache, in the writable /tmp like Vite's.
    fsModuleCachePath: "/tmp/vitest",
    // Tests must never reach a real server.
    restoreMocks: true,
  },
});
