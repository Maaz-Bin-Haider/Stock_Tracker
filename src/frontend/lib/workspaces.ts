/**
 * Registry of the workspaces an employee can move between.
 *
 * Mirrors home/workspaces.py in the Accounting ERP repository — the two lists
 * are maintained by hand and are expected to describe the same systems.
 *
 * To add a third system
 * ---------------------
 * 1. Append an entry below (and the matching entry in the ERP's registry).
 * 2. Pick any `accent` from the four defined in app/globals.css, and any
 *    `icon` from ICON_PATHS — add one there if none fits.
 * 3. Rebuild the frontend. Nothing else changes: the sidebar switcher shows a
 *    hover menu automatically once more than one other workspace exists.
 */

export type WorkspaceAccent = "blue" | "emerald" | "amber" | "violet";
export type WorkspaceIcon = "ledger" | "boxes" | "chart";

export interface Workspace {
  id: string;
  name: string;
  tagline: string;
  modules: string[];
  icon: WorkspaceIcon;
  accent: WorkspaceAccent;
  url: string;
  /** True when arriving does not require typing a password again. */
  signsIn: boolean;
}

/** 24x24 stroke paths, so no icon font is needed. */
export const ICON_PATHS: Record<WorkspaceIcon, string[]> = {
  ledger: [
    "M4 19.5A2.5 2.5 0 0 1 6.5 17H20",
    "M4 19.5V5a2 2 0 0 1 2-2h12a2 2 0 0 1 2 2v12H6.5A2.5 2.5 0 0 0 4 19.5Z",
  ],
  boxes: [
    "M21 8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16Z",
    "M3.3 7 12 12l8.7-5",
    "M12 22V12",
  ],
  chart: ["M3 3v18h18", "M18 17V9", "M13 17V5", "M8 17v-3"],
};

/** Which workspace this application *is*. */
export const CURRENT_WORKSPACE_ID = "stock";

// The ERP's address. Inlined at build time; the default is the live host, so a
// rebuild is only needed if the domain itself ever changes.
const ERP_URL = process.env.NEXT_PUBLIC_ERP_URL || "https://swisstechfinance.com/";

export const WORKSPACES: Workspace[] = [
  {
    id: "erp",
    name: "Accounting ERP",
    tagline: "Invoicing, payments and the financial books.",
    modules: ["Sales", "Purchase", "Finance", "Accounting"],
    icon: "ledger",
    accent: "blue",
    url: ERP_URL,
    // Anyone who reached the Stock Tracker through the ERP still holds a live
    // ERP session, so they arrive signed in. Someone who logged in directly
    // here will see the ERP's login page — trust is deliberately
    // one-directional, so this system never asserts identity to the ERP.
    signsIn: false,
  },
  {
    id: "stock",
    name: "Stock Tracker",
    tagline: "Stock ledger, shipments and inventory movement.",
    modules: ["Stock", "Shipment", "Inventory"],
    icon: "boxes",
    accent: "emerald",
    url: "/",
    signsIn: true,
  },
];

export function currentWorkspace(): Workspace {
  const found = WORKSPACES.find((w) => w.id === CURRENT_WORKSPACE_ID);
  if (!found) throw new Error(`CURRENT_WORKSPACE_ID "${CURRENT_WORKSPACE_ID}" is not in WORKSPACES`);
  return found;
}

/** Everywhere an employee can switch to from here. */
export function otherWorkspaces(): Workspace[] {
  return WORKSPACES.filter((w) => w.id !== CURRENT_WORKSPACE_ID && w.url);
}
