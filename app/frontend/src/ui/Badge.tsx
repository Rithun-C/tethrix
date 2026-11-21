import type { ReactNode } from "react";

// Satrix UI badge: a short label. Status never depends on colour alone, so every badge
// carries a word.

export type BadgeTone = "default" | "secondary" | "outline" | "danger";

export function Badge({ tone = "secondary", children }: { tone?: BadgeTone; children: ReactNode }) {
  return <span className={`badge badge-${tone}`}>{children}</span>;
}
