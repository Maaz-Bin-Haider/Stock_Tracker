"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { api } from "@/lib/api";
import { AuthContext, type SessionUser } from "@/lib/auth";
import { applyTheme, isDarkActive, type ThemePreference } from "@/lib/theme";

const NAV: { href: string; label: string; adminOnly?: boolean }[] = [
  { href: "/", label: "Dashboard" },
  { href: "/products", label: "Products" },
  { href: "/purchases", label: "Purchases" },
  { href: "/purchase-collection", label: "Collection / Pending" },
  { href: "/purchase-refunds", label: "Refunds / Cancellations" },
  { href: "/shipments", label: "Shipments" },
  { href: "/sales", label: "Sales" },
  { href: "/stock-ledger", label: "Stock Ledger" },
  { href: "/stock-adjustments", label: "Stock Adjustments" },
  { href: "/reports", label: "Reports" },
  { href: "/valuation", label: "Stock Valuation", adminOnly: true },
  { href: "/suppliers", label: "Suppliers" },
  { href: "/customers", label: "Customers" },
  { href: "/settings/categories", label: "Categories" },
  { href: "/settings/locations", label: "Locations" },
  { href: "/settings/currencies", label: "Currencies" },
  { href: "/settings/exchange-rates", label: "Exchange Rates" },
  { href: "/settings/gst-rates", label: "GST Rates" },
  { href: "/users", label: "Users", adminOnly: true },
  { href: "/audit", label: "Audit Activity" },
];

export default function AppLayout({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const [user, setUser] = useState<SessionUser | null>(null);
  const [loading, setLoading] = useState(true);
  const [menuOpen, setMenuOpen] = useState(false);

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
    <aside className="flex h-full w-56 shrink-0 flex-col border-r border-edge bg-surface">
      <div className="border-b border-edge px-4 py-4">
        <div className="text-sm font-semibold">SwissTech</div>
        <div className="text-xs text-muted">Stock Tracker</div>
      </div>
      <nav className="flex-1 overflow-y-auto p-2 text-sm">
        {NAV.filter((item) => !item.adminOnly || user?.role === "ADMIN").map((item) => (
          <Link
            key={item.href}
            href={item.href}
            className={`block rounded px-3 py-1.5 ${
              pathname === item.href
                ? "bg-primary-soft font-medium text-primary"
                : "text-ink-2 hover:bg-surface-2"
            }`}
          >
            {item.label}
          </Link>
        ))}
      </nav>
      <div className="border-t border-edge p-4 text-sm">
        <div className="flex items-center justify-between gap-2">
          <div>
            <div className="font-medium">{user?.username}</div>
            <div className="text-xs text-muted">{user?.role}</div>
          </div>
          <button
            onClick={toggleTheme}
            className="rounded border border-edge px-2 py-1 text-xs text-ink-2 hover:bg-surface-2"
            title="Switch between the light and dark theme"
          >
            {user?.theme === "DARK" ? "Light mode" : "Dark mode"}
          </button>
        </div>
        <button onClick={logout} className="mt-2 text-xs text-primary hover:underline">
          Sign out
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
              className="rounded border border-edge px-2.5 py-1.5 text-sm text-ink-2"
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
