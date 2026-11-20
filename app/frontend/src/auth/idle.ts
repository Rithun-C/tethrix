// Sign out after a time without user activity (ADR-0003 decision 5, SR-05).
//
// Activity is a click, a key press, a scroll or a touch. The check runs every minute and
// also whenever the tab becomes visible again, because browsers slow down timers in
// background tabs.

import { useEffect } from "react";

export const IDLE_LIMIT_MS = 60 * 60 * 1000;
const CHECK_EVERY_MS = 60 * 1000;
const ACTIVITY_EVENTS = ["pointerdown", "keydown", "wheel", "touchstart"] as const;

export function useIdleSignOut(active: boolean, onIdle: () => void, limitMs = IDLE_LIMIT_MS): void {
  useEffect(() => {
    if (!active) return;
    let last = Date.now();
    let fired = false;

    const touch = () => {
      last = Date.now();
    };
    const check = () => {
      if (!fired && Date.now() - last >= limitMs) {
        fired = true;
        onIdle();
      }
    };

    for (const name of ACTIVITY_EVENTS) window.addEventListener(name, touch, { passive: true });
    document.addEventListener("visibilitychange", check);
    const timer = window.setInterval(check, CHECK_EVERY_MS);

    return () => {
      for (const name of ACTIVITY_EVENTS) window.removeEventListener(name, touch);
      document.removeEventListener("visibilitychange", check);
      window.clearInterval(timer);
    };
  }, [active, onIdle, limitMs]);
}
