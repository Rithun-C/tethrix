import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter } from "react-router";

import { App } from "./App";
import { AuthProvider } from "./auth/AuthProvider";
import { OidcAuthService } from "./auth/service";
import "./styles.css";

const root = document.getElementById("root");
if (!root) throw new Error("index.html has no #root element");

createRoot(root).render(
  // StrictMode runs extra checks in development (for example it runs effects twice to
  // reveal missing clean-up). It does nothing in the production build.
  <StrictMode>
    <AuthProvider service={new OidcAuthService()}>
      <BrowserRouter>
        <App />
      </BrowserRouter>
    </AuthProvider>
  </StrictMode>,
);
