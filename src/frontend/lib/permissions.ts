import type { Role } from "./auth";

/**
 * UI mirror of the backend ROLE_MATRIX (accounts/permissions.py) for
 * menu/action visibility only — the server remains the enforcement point.
 */
const WRITE_ACCESS: Record<string, Role[]> = {
  categories: ["ADMIN", "PURCHASE", "SALE"],
  locations: ["ADMIN"],
  currencies: ["ADMIN"],
  "exchange-rates": ["ADMIN", "PURCHASE", "SALE"],
  "gst-rates": ["ADMIN", "PURCHASE", "SALE"],
  suppliers: ["ADMIN", "PURCHASE"],
  customers: ["ADMIN", "SALE"],
  products: ["ADMIN", "PURCHASE"],
  purchases: ["ADMIN", "PURCHASE"],
  shipments: ["ADMIN", "PURCHASE"],
  users: ["ADMIN"],
};

export function canWrite(role: Role | undefined, module: string): boolean {
  if (!role) return false;
  return (WRITE_ACCESS[module] ?? ["ADMIN"]).includes(role);
}
