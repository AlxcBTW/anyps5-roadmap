import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { App } from "./App";
import { adoptLegacyHash } from "./lib/router";
import "./styles/tokens.css";
import "./styles/app.css";

adoptLegacyHash();
createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
