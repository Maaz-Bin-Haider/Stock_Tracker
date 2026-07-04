"use client";

import { useAuth } from "@/lib/auth";

export default function DashboardPage() {
  const user = useAuth();

  return (
    <div>
      <h1 className="mb-1 text-xl font-semibold">Dashboard</h1>
      <p className="mb-6 text-sm text-slate-500">
        Welcome back, <span className="font-medium">{user?.username}</span> ({user?.role}).
      </p>
      <div className="rounded-lg border border-dashed border-slate-300 bg-white p-8 text-center text-sm text-slate-400">
        Live stock cards (total, by location, pending, in-transit, today&apos;s sales) arrive
        with the reports milestone. Master data, products, users, and audit activity are ready
        in the sidebar.
      </div>
    </div>
  );
}
