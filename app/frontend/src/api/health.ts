import { useEffect, useState } from "react";

import { apiFetch } from "./client";

export type ApiStatus = "checking" | "ok" | "unreachable";

interface HealthResponse {
  status: string;
}

/** Asks the backend's health endpoint once, when the component appears. */
export function useApiStatus(): ApiStatus {
  const [status, setStatus] = useState<ApiStatus>("checking");

  useEffect(() => {
    // If the user leaves the page before the answer arrives, cancel the request so
    // nothing tries to update a component that is gone.
    const controller = new AbortController();

    apiFetch<HealthResponse>("/health", { signal: controller.signal }).then(
      (body) => {
        setStatus(body.status === "ok" ? "ok" : "unreachable");
      },
      () => {
        if (!controller.signal.aborted) setStatus("unreachable");
      },
    );

    return () => {
      controller.abort();
    };
  }, []);

  return status;
}
