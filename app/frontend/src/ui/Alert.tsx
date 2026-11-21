import type { ReactNode } from "react";

// Satrix UI alert: an inline message about this page. The tone shows in colour, icon
// and words; errors use role="alert" so screen readers announce them at once.

interface AlertProps {
  tone?: "info" | "danger";
  title: string;
  children?: ReactNode;
  action?: ReactNode;
}

export function Alert({ tone = "info", title, children, action }: AlertProps) {
  return (
    <div className={`alert alert-${tone}`} role={tone === "danger" ? "alert" : "status"}>
      <span className="alert-disc" aria-hidden="true">
        {tone === "danger" ? "!" : "i"}
      </span>
      <div className="alert-body">
        <span className="alert-title">{title}</span>
        {children && <span className="alert-text">{children}</span>}
      </div>
      {action}
    </div>
  );
}
