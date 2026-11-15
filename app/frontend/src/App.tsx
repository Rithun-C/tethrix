import { Route, Routes } from "react-router";

import { Layout } from "./components/Layout";
import { DashboardPage } from "./pages/DashboardPage";
import { NotFoundPage } from "./pages/NotFoundPage";
import { PlaceholderPage } from "./pages/PlaceholderPage";

/** Which page is shown for which address. */
export function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route index element={<DashboardPage />} />
        <Route path="todos" element={<PlaceholderPage title="Todos" bolt="B5" />} />
        <Route path="habits" element={<PlaceholderPage title="Habits" bolt="B7" />} />
        <Route path="journal" element={<PlaceholderPage title="Journal" bolt="B8" />} />
        <Route path="pages" element={<PlaceholderPage title="Pages" bolt="B8" />} />
        <Route path="*" element={<NotFoundPage />} />
      </Route>
    </Routes>
  );
}
