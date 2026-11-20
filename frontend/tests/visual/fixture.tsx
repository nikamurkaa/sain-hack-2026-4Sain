import React from "react";
import { createRoot } from "react-dom/client";
import "../../src/style.css";
import { DesignScreen } from "../../src/design/Layout";
// This standalone Vite test entry is excluded from the production build.
const frame = Number(new URL(location.href).searchParams.get("frame"));
if (!Number.isInteger(frame) || frame < 1 || frame > 29)
  throw Error("Unknown Figma frame");
createRoot(document.getElementById("root")!).render(
  <DesignScreen screen={frame} />,
);
