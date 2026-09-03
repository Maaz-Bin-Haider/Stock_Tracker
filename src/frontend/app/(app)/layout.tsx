"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useMemo, useState } from "react";

import NavIcon, { type NavIconName } from "@/components/nav-icon";
import WorkspaceSwitcher from "@/components/workspace-switcher";
import { api } from "@/lib/api";
import { AuthContext, type SessionUser } from "@/lib/auth";
import { applyTheme, isDarkActive, type ThemePreference } from "@/lib/theme";

const NAV: { href: string; label: string; icon: NavIconName; adminOnly?: boolean }[] = [
  { href: "/", label: "Dashboard", icon: "dashboard" },
  { href: "/products", label: "Products", icon: "products" },
  { href: "/purchases", label: "Purchases", icon: "purchases" },
  { href: "/purchase-collection", label: "Collection / Pending", icon: "collection" },
  { href: "/purchase-refunds", label: "Refunds / Cancellations", icon: "refunds" },
  { href: "/shipments", label: "Shipments", icon: "shipments" },
  { href: "/sales", label: "Sales", icon: "sales" },
  { href: "/stock-ledger", label: "Stock Ledger", icon: "ledger" },
  { href: "/stock-adjustments", label: "Stock Adjustments", icon: "adjustments" },
  { href: "/reports", label: "Reports", icon: "reports" },
  { href: "/valuation", label: "Stock Valuation", icon: "valuation", adminOnly: true },
  { href: "/suppliers", label: "Suppliers", icon: "suppliers" },
  { href: "/customers", label: "Customers", icon: "customers" },
  { href: "/settings/categories", label: "Categories", icon: "categories" },
  { href: "/settings/locations", label: "Locations", icon: "locations" },
  { href: "/settings/currencies", label: "Currencies", icon: "currencies" },
  { href: "/settings/exchange-rates", label: "Exchange Rates", icon: "exchange" },
  { href: "/settings/gst-rates", label: "GST Rates", icon: "gst" },
  { href: "/users", label: "Users", icon: "users", adminOnly: true },
  { href: "/audit", label: "Audit Activity", icon: "audit" },
];

export default function AppLayout({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const [user, setUser] = useState<SessionUser | null>(null);
  const [loading, setLoading] = useState(true);
  const [menuOpen, setMenuOpen] = useState(false);
  const [filter, setFilter] = useState("");

  useEffect(() => {
    api<SessionUser>("/api/v1/auth/me/")
      .then((me) => {
        setUser(me);
        setLoading(false);
        // The profile preference wins over localStorage so the theme follows
        // the user across devices (FR-126).
        if (me.theme) applyTheme(me.theme);
      })
      .catch(() => router.replace("/login"));
  }, [router]);

  // Close the drawer on navigation (small screens).
  useEffect(() => {
    setMenuOpen(false);
  }, [pathname]);

  const items = useMemo(() => {
    const allowed = NAV.filter((item) => !item.adminOnly || user?.role === "ADMIN");
    const q = filter.trim().toLowerCase();
    return q ? allowed.filter((item) => item.label.toLowerCase().includes(q)) : allowed;
  }, [user, filter]);

  async function toggleTheme() {
    const next: ThemePreference = isDarkActive() ? "LIGHT" : "DARK";
    applyTheme(next);
    if (user) {
      setUser({ ...user, theme: next });
      await api("/api/v1/auth/me/", { method: "PATCH", body: { theme: next } }).catch(
        () => undefined,
      );
    }
  }

  async function logout() {
    await api("/api/v1/auth/logout/", { method: "POST" }).catch(() => undefined);
    router.replace("/login");
  }

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center text-sm text-muted">
        Loading…
      </div>
    );
  }

  const sidebar = (
    <aside className="app-sidebar flex h-full w-[248px] shrink-0 flex-col">
      {/* Brand */}
      <div className="border-b border-sidebar-border px-4 pb-4 pt-5">
        <div className="mb-3 flex items-center justify-center gap-2.5">
          <span className="flex h-8 w-8 items-center justify-center rounded-md bg-gradient-to-br from-primary to-[#0ea5e9] text-white shadow-[0_4px_14px_rgba(37,99,235,0.3)]">
            <NavIcon name="products" size={17} />
          </span>
          <span className="text-[1.05rem] font-bold tracking-tight text-white">Stock Tracker</span>
        </div>
        <label className="relative block">
          <span className="sr-only">Filter navigation</span>
          <input
            value={filter}
            onChange={(event) => setFilter(event.target.value)}
            placeholder="Search…"
            className="w-full rounded-md border-0 bg-[rgba(255,255,255,0.07)] px-3 py-1.5 text-[0.8rem] text-sidebar-text placeholder:text-[rgba(226,232,240,0.45)] focus:outline-none focus:ring-1 focus:ring-primary"
          />
        </label>
      </div>

      {/* Switch workspace */}
      <WorkspaceSwitcher />

      {/* Navigation */}
      <nav className="flex-1 overflow-y-auto px-3 py-3.5">
        {items.map((item) => {
          const active = pathname === item.href;
          return (
            <Link
              key={item.href}
              href={item.href}
              className={`mb-0.5 flex items-center gap-2.5 whitespace-nowrap rounded-md px-3 py-[0.58rem] text-[0.875rem] transition-colors ${
                active
                  ? "bg-sidebar-active-bg font-medium text-sidebar-active-text"
                  : "text-sidebar-link hover:bg-[rgba(255,255,255,0.06)] hover:text-white"
              }`}
            >
              <NavIcon name={item.icon} />
              {item.label}
            </Link>
          );
        })}
        {items.length === 0 && (
          <p className="px-3 py-2 text-[0.78rem] text-sidebar-link opacity-60">No matches.</p>
        )}
      </nav>

      {/* Footer */}
      <div className="border-t border-sidebar-border px-3 pb-4 pt-3.5">
        <div className="flex items-center gap-2 rounded-md bg-[rgba(255,255,255,0.05)] px-3 py-2">
          <NavIcon name="users" size={13} />
          <span className="min-w-0 flex-1 truncate text-[0.82rem] text-sidebar-text">
            {user?.username}
          </span>
          <span className="text-[0.62rem] uppercase tracking-wider text-sidebar-link opacity-70">
            {user?.role}
          </span>
        </div>
        <button
          onClick={toggleTheme}
          className="mt-2 flex w-full items-center gap-2 rounded-md px-3 py-2 text-[0.8rem] text-sidebar-link transition-colors hover:bg-[rgba(255,255,255,0.06)] hover:text-white"
          title="Switch between the light and dark theme"
        >
          <span aria-hidden="true">{user?.theme === "DARK" ? "☀" : "☾"}</span>
          {user?.theme === "DARK" ? "Light Mode" : "Dark Mode"}
        </button>
        <button
          onClick={logout}
          className="mt-0.5 flex w-full items-center gap-2 rounded-md px-3 py-2 text-[0.8rem] text-danger transition-colors hover:bg-[rgba(248,113,113,0.12)]"
        >
          <span aria-hidden="true">⏻</span> Logout
        </button>
      </div>
    </aside>
  );

  return (
    <AuthContext.Provider value={user}>
      <div className="flex min-h-screen">
        {/* Static sidebar on desktop */}
        <div className="hidden lg:block">{sidebar}</div>

        {/* Drawer on tablets/phones (SRS §7.6) */}
        {menuOpen && (
          <div className="fixed inset-0 z-40 flex lg:hidden">
            <div className="h-full">{sidebar}</div>
            <button
              aria-label="Close menu"
              className="flex-1 bg-black/40"
              onClick={() => setMenuOpen(false)}
            />
          </div>
        )}

        <div className="flex min-w-0 flex-1 flex-col">
          <header className="flex items-center gap-3 border-b border-edge bg-surface px-4 py-3 lg:hidden">
            <button
              aria-label="Open menu"
              className="rounded-md border border-edge px-2.5 py-1.5 text-sm text-ink-2"
              onClick={() => setMenuOpen(true)}
            >
              ☰
            </button>
            <div className="text-sm font-semibold">SwissTech Stock Tracker</div>
          </header>
          <main className="min-w-0 flex-1 overflow-x-hidden p-4 lg:p-6">{children}</main>
        </div>
      </div>
    </AuthContext.Provider>
  );
}
