import { useApiStatus, type ApiStatus } from "../api/health";
import { useMe } from "../api/me";

const STATUS_TEXT: Record<ApiStatus, string> = {
  checking: "checking...",
  ok: "ok",
  unreachable: "unreachable",
};

export function DashboardPage() {
  const status = useApiStatus();
  const me = useMe();

  return (
    <>
      <h1>Dashboard</h1>
      <p>Nothing here yet. The dashboard is built in bolt B9.</p>
      {me && <p className="profile">Your time zone: {me.timeZone ?? "not set"}</p>}
      {/* role="status" makes screen readers announce the text when it changes. */}
      <p role="status" className={`api-status api-status-${status}`}>
        API: {STATUS_TEXT[status]}
      </p>
    </>
  );
}
