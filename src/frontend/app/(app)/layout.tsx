"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { api } from "@/lib/api";
import { AuthContext, type SessionUser } from "@/lib/auth";

const NAV: { href: string; label: string; adminOnly?: boolean }[] = [
  { href: "/", label: "Dashboard" },
  { href: "/products", label: "Products" },
  { href: "/purchases", label: "Purchases" },
  { href: "/purchase-collection", label: "Collection / Pending" },
  { href: "/purchase-refunds", label: "Refunds / Cancellations" },
  { href: "/stock-ledger", label: "Stock Ledger" },
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

  useEffect(() => {
    api<SessionUser>("/api/v1/auth/me/")
      .then((me) => {
        setUser(me);
        setLoading(false);
      })
      .catch(() => router.replace("/login"));
  }, [router]);

  async function logout() {
    await api("/api/v1/auth/logout/", { method: "POST" }).catch(() => undefined);
    router.replace("/login");
  }

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center text-sm text-slate-500">
        Loading…
      </div>
    );
  }

  return (
    <AuthContext.Provider value={user}>
      <div className="flex min-h-screen">
        <aside className="flex w-56 shrink-0 flex-col border-r border-slate-200 bg-white">
          <div className="border-b border-slate-200 px-4 py-4">
            <div className="text-sm font-semibold">SwissTech</div>
            <div className="text-xs text-slate-500">Stock Tracker</div>
          </div>
          <nav className="flex-1 overflow-y-auto p-2 text-sm">
            {NAV.filter((item) => !item.adminOnly || user?.role === "ADMIN").map((item) => (
              <Link
                key={item.href}
                href={item.href}
                className={`block rounded px-3 py-1.5 ${
                  pathname === item.href
                    ? "bg-blue-50 font-medium text-blue-700"
                    : "text-slate-600 hover:bg-slate-50"
                }`}
              >
                {item.label}
              </Link>
            ))}
          </nav>
          <div className="border-t border-slate-200 p-4 text-sm">
            <div className="font-medium">{user?.username}</div>
            <div className="mb-2 text-xs text-slate-500">{user?.role}</div>
            <button onClick={logout} className="text-xs text-blue-700 hover:underline">
              Sign out
            </button>
          </div>
        </aside>
        <main className="flex-1 overflow-x-hidden p-6">{children}</main>
      </div>
    </AuthContext.Provider>
  );
}
