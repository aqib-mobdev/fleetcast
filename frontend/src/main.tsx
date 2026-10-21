import "@fontsource-variable/space-grotesk";
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { SWRConfig } from "swr";
import App from "./App";
import "./index.css";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <SWRConfig value={{ revalidateOnFocus: false, shouldRetryOnError: false }}>
      <App />
    </SWRConfig>
  </StrictMode>,
);
