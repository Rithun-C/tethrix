import { Route, Routes } from "react-router";

import { Layout } from "./components/Layout";
import { RequireAuth } from "./components/RequireAuth";
import { CallbackPage } from "./pages/CallbackPage";
import { DashboardPage } from "./pages/DashboardPage";
import { NotFoundPage } from "./pages/NotFoundPage";
import { PlaceholderPage } from "./pages/PlaceholderPage";
import { TodosPage } from "./pages/TodosPage";

/** Which page is shown for which address. */
export function App() {
  return (
    <Routes>
      {/* Open: the sign-in server sends the browser back here. */}
      <Route path="auth/callback" element={<CallbackPage />} />
      {/* Everything else needs a sign-in (B4). */}
      <Route element={<RequireAuth />}>
        <Route element={<Layout />}>
          <Route index element={<DashboardPage />} />
          <Route path="todos" element={<TodosPage />} />
          <Route path="habits" element={<PlaceholderPage title="Habits" bolt="B7" />} />
          <Route path="journal" element={<PlaceholderPage title="Journal" bolt="B8" />} />
          <Route path="pages" element={<PlaceholderPage title="Pages" bolt="B8" />} />
          <Route path="*" element={<NotFoundPage />} />
        </Route>
      </Route>
    </Routes>
  );
}
