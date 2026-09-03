/**
 * Navigation glyphs.
 *
 * The Accounting ERP's sidebar pairs every item with an icon; this gives the
 * Stock Tracker the same silhouette without pulling in an icon font. Paths are
 * 24x24 stroke outlines so they inherit `currentColor` and line up with the
 * ERP's Font Awesome set at the same optical weight.
 */

export type NavIconName =
  | "dashboard" | "products" | "purchases" | "collection" | "refunds"
  | "shipments" | "sales" | "ledger" | "adjustments" | "reports"
  | "valuation" | "suppliers" | "customers" | "categories" | "locations"
  | "currencies" | "exchange" | "gst" | "users" | "audit";

const PATHS: Record<NavIconName, string[]> = {
  dashboard: ["m3 9 9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z", "M9 22V12h6v10"],
  products: [
    "M21 8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16Z",
    "M3.3 7 12 12l8.7-5", "M12 22V12",
  ],
  purchases: ["M6 2 3 6v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2V6l-3-4Z", "M3 6h18", "M16 10a4 4 0 0 1-8 0"],
  collection: ["M12 22a10 10 0 1 0 0-20 10 10 0 0 0 0 20Z", "M12 6v6l4 2"],
  refunds: ["M3 12a9 9 0 1 0 3-6.7L3 8", "M3 3v5h5"],
  shipments: [
    "M14 18V6a1 1 0 0 0-1-1H2a1 1 0 0 0-1 1v11a1 1 0 0 0 1 1h2",
    "M14 9h4l3 3v5a1 1 0 0 1-1 1h-1",
    "M7 19a2 2 0 1 0 0-4 2 2 0 0 0 0 4Z", "M17 19a2 2 0 1 0 0-4 2 2 0 0 0 0 4Z",
  ],
  sales: [
    "M8 21a1 1 0 1 0 0-2 1 1 0 0 0 0 2Z", "M19 21a1 1 0 1 0 0-2 1 1 0 0 0 0 2Z",
    "M2 3h2l2.6 12.4a2 2 0 0 0 2 1.6h8.8a2 2 0 0 0 2-1.6L21 7H6",
  ],
  ledger: ["M8 6h13", "M8 12h13", "M8 18h13", "M3 6h.01", "M3 12h.01", "M3 18h.01"],
  adjustments: ["M4 21v-7", "M4 10V3", "M12 21v-9", "M12 8V3", "M20 21v-5", "M20 12V3", "M1 14h6", "M9 8h6", "M17 16h6"],
  reports: ["M3 3v18h18", "M18 17V9", "M13 17V5", "M8 17v-3"],
  valuation: [
    "M12 8c3.9 0 7-1.3 7-3s-3.1-3-7-3-7 1.3-7 3 3.1 3 7 3Z",
    "M5 5v6c0 1.7 3.1 3 7 3s7-1.3 7-3V5", "M5 11v6c0 1.7 3.1 3 7 3s7-1.3 7-3v-6",
  ],
  suppliers: ["M3 21h18", "M5 21V7l7-4 7 4v14", "M9 21v-6h6v6"],
  customers: [
    "M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2",
    "M9 11a4 4 0 1 0 0-8 4 4 0 0 0 0 8Z", "M22 21v-2a4 4 0 0 0-3-3.87",
  ],
  categories: [
    "m20.6 13.4-7.2 7.2a2 2 0 0 1-2.8 0l-8.2-8.2A2 2 0 0 1 2 11V4a2 2 0 0 1 2-2h7a2 2 0 0 1 1.4.6l8.2 8.2a2 2 0 0 1 0 2.6Z",
    "M7 7h.01",
  ],
  locations: ["M20 10c0 6-8 12-8 12s-8-6-8-12a8 8 0 0 1 16 0Z", "M12 13a3 3 0 1 0 0-6 3 3 0 0 0 0 6Z"],
  currencies: ["M12 2v20", "M17 7H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"],
  exchange: ["M8 3 4 7l4 4", "M4 7h16", "m16 21 4-4-4-4", "M20 17H4"],
  gst: ["m19 5-14 14", "M6.5 9a2.5 2.5 0 1 0 0-5 2.5 2.5 0 0 0 0 5Z", "M17.5 20a2.5 2.5 0 1 0 0-5 2.5 2.5 0 0 0 0 5Z"],
  users: ["M19 21v-2a4 4 0 0 0-4-4H9a4 4 0 0 0-4 4v2", "M12 11a4 4 0 1 0 0-8 4 4 0 0 0 0 8Z"],
  audit: ["M22 12h-4l-3 9L9 3l-3 9H2"],
};

export default function NavIcon({ name, size = 16 }: { name: NavIconName; size?: number }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={1.7}
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      className="shrink-0"
    >
      {PATHS[name].map((d) => (
        <path key={d} d={d} />
      ))}
    </svg>
  );
}
