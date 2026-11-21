import type { InputHTMLAttributes } from "react";

// Satrix UI checkbox: a small rectangle with the orbit corner (only celestial things are
// round). A real <input type="checkbox">, styled, so keyboard and screen readers work.

export function Checkbox(props: Omit<InputHTMLAttributes<HTMLInputElement>, "type">) {
  return (
    <input type="checkbox" {...props} className={`checkbox ${props.className ?? ""}`.trim()} />
  );
}
