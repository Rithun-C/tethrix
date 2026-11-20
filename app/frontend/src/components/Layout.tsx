import { NavLink, Outlet } from "react-router";

import { useAuth } from "../auth/AuthProvider";

const LINKS = [
  { to: "/", label: "Dashboard" },
  { to: "/todos", label: "Todos" },
  { to: "/habits", label: "Habits" },
  { to: "/journal", label: "Journal" },
  { to: "/pages", label: "Pages" },
] as const;

/** The frame around every screen: the menu on the left, the current page on the right. */
export function Layout() {
  const { user, signOut } = useAuth();

  return (
    <div className="layout">
      <nav className="menu" aria-label="Main">
        <p className="menu-title">Productivity app</p>
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
          <button type="button" onClick={signOut}>
            Sign out
          </button>
        </div>
      </nav>
      <main className="content">
        {/* React Router puts the page for the current address here. */}
        <Outlet />
      </main>
    </div>
  );
}
