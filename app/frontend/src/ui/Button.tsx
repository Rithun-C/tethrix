import type { ButtonHTMLAttributes } from "react";

// Satrix UI button (owner's component library, docs/bolts/B5-todos.md section 15):
// the orbit corner, one primary per view, labels as verbs.

export type ButtonVariant = "primary" | "secondary" | "outline" | "ghost" | "danger";

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant;
  size?: "sm" | "md";
}

export function Button({
  variant = "outline",
  size = "md",
  type = "button",
  className,
  ...rest
}: ButtonProps) {
  const classes = ["btn", `btn-${variant}`, size === "sm" ? "btn-sm" : "", className ?? ""]
    .filter(Boolean)
    .join(" ");
  return <button type={type} className={classes} {...rest} />;
}
