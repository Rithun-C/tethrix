import { useEffect, useState } from "react";

import { apiFetch } from "./client";

export interface Me {
  userId: string;
  timeZone: string | null;
  createdAt: string | null;
}

/** The signed-in user's profile (GET /api/v1/me), or null while loading or on error. */
export function useMe(): Me | null {
  const [me, setMe] = useState<Me | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    apiFetch<Me>("/me", { signal: controller.signal }).then(setMe, () => {
      if (!controller.signal.aborted) setMe(null);
    });
    return () => {
      controller.abort();
    };
  }, []);

  return me;
}
