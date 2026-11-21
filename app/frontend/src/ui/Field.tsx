import { useId, type ReactNode } from "react";

// Satrix UI label, input, textarea and select. The label stays visible above the field;
// an optional field says so in words; help and errors sit below.

interface FieldProps {
  label: string;
  optional?: boolean;
  /** Renders the control, given the id the label points at. */
  children: (id: string) => ReactNode;
  className?: string;
}

export function Field({ label, optional, children, className }: FieldProps) {
  const id = useId();
  return (
    <div className={`field ${className ?? ""}`.trim()}>
      <label htmlFor={id} className="field-label">
        {label}
        {optional && <span className="field-optional">Optional</span>}
      </label>
      {children(id)}
    </div>
  );
}
