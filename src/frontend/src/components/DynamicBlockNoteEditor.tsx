import { lazy } from "react";

// Dynamically import BlockNote editor to avoid SSR issues
export const BlockNoteEditor = lazy(() => import("./BlockNoteEditor"));
