import { useApiStatus, type ApiStatus } from "../api/health";

const STATUS_TEXT: Record<ApiStatus, string> = {
  checking: "checking...",
  ok: "ok",
  unreachable: "unreachable",
};

export function DashboardPage() {
  const status = useApiStatus();

  return (
    <>
      <h1>Dashboard</h1>
      <p>Nothing here yet. The dashboard is built in bolt B9.</p>
      {/* role="status" makes screen readers announce the text when it changes. */}
      <p role="status" className={`api-status api-status-${status}`}>
        API: {STATUS_TEXT[status]}
      </p>
    </>
  );
}
