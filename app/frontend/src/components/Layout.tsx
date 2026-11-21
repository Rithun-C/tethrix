import { NavLink, Outlet } from "react-router";

import { useAuth } from "../auth/AuthProvider";
import { TethrixLogo } from "../brand/Logo";
import { Button } from "../ui/Button";
import { ToastProvider } from "../ui/Toast";

const LINKS = [
  { to: "/", label: "Dashboard" },
  { to: "/todos", label: "Todos" },
  { to: "/habits", label: "Habits" },
  { to: "/journal", label: "Journal" },
  { to: "/pages", label: "Pages" },
] as const;

/**
 * The frame around every screen: the menu on the left (the Satrix UI sidebar: items on an
 * orbit line, a moon beside the current one), the current page on the right.
 */
export function Layout() {
  const { user, signOut } = useAuth();

  return (
    <ToastProvider>
      <div className="layout">
        <nav className="menu" aria-label="Main">
          <p className="menu-title">
            <TethrixLogo size={36} />
          </p>
          <ul>
            {LINKS.map((link) => (
              <li key={link.to}>
                <NavLink to={link.to} end={link.to === "/"}>
                  {link.label}
                </NavLink>
              </li>
            ))}
          </ul>
          <div className="menu-account">
            {user?.email && <p className="menu-user">{user.email}</p>}
            <Button size="sm" onClick={signOut}>
              Sign out
            </Button>
          </div>
        </nav>
        <main className="content">
          {/* React Router puts the page for the current address here. */}
          <Outlet />
        </main>
      </div>
    </ToastProvider>
  );
}
