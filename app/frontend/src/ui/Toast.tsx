import { createContext, useCallback, useContext, useRef, useState, type ReactNode } from "react";

// Satrix UI toast: a brief message after an action, bottom right, at most three, gone
// after five seconds. Errors use role="alert".

export interface ToastMessage {
  id: number;
  tone: "info" | "danger";
  title: string;
  text?: string;
}

type Show = (toast: Omit<ToastMessage, "id">) => void;

const ToastContext = createContext<Show>(() => undefined);

export const TOAST_MS = 5000;
const MAX_TOASTS = 3;

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<ToastMessage[]>([]);
  const next = useRef(1);

  const dismiss = useCallback((id: number) => {
    setToasts((current) => current.filter((t) => t.id !== id));
  }, []);

  const show = useCallback<Show>(
    (toast) => {
      const id = next.current++;
      setToasts((current) => [...current, { ...toast, id }].slice(-MAX_TOASTS));
      setTimeout(() => {
        dismiss(id);
      }, TOAST_MS);
    },
    [dismiss],
  );

  return (
    <ToastContext.Provider value={show}>
      {children}
      <div className="toasts">
        {toasts.map((toast) => (
          <div
            key={toast.id}
            className={`toast toast-${toast.tone}`}
            role={toast.tone === "danger" ? "alert" : "status"}
          >
            <span className="toast-moon" aria-hidden="true" />
            <div className="toast-body">
              <span className="toast-title">{toast.title}</span>
              {toast.text && <span className="toast-text">{toast.text}</span>}
            </div>
            <button
              type="button"
              className="btn btn-ghost btn-sm"
              onClick={() => {
                dismiss(toast.id);
              }}
            >
              Dismiss
            </button>
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  );
}

/** Shows a toast. Works anywhere under ToastProvider. */
export function useToast(): Show {
  return useContext(ToastContext);
}
