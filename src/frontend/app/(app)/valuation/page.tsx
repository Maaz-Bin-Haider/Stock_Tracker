"use client";

import { useEffect, useState } from "react";

import ReportView, { type ReportMeta } from "@/components/report-view";
import { api, errorMessage } from "@/lib/api";
import { useAuth } from "@/lib/auth";

/**
 * Admin-only Stock Valuation section (FR-115…FR-123). The server enforces the
 * restriction on every data and export endpoint — this page only mirrors it.
 */
export default function ValuationPage() {
  const user = useAuth();
  const [reports, setReports] = useState<ReportMeta[]>([]);
  const [tab, setTab] = useState("stock-valuation-summary");
  const [error, setError] = useState("");

  useEffect(() => {
    api<ReportMeta[]>("/api/v1/reports/")
      .then((body) => setReports(body.filter((report) => report.admin_only)))
      .catch((err) => setError(errorMessage(err)));
  }, []);

  if (user && user.role !== "ADMIN") {
    return (
      <p className="text-sm text-slate-500">
        Stock valuation is available to admin users only.
      </p>
    );
  }

  const selected = reports.find((report) => report.key === tab);

  return (
    <div>
      <div className="mb-1 flex items-center gap-3">
        <h1 className="text-xl font-semibold">Stock Valuation</h1>
        <span className="rounded bg-slate-100 px-2 py-0.5 text-xs font-medium text-slate-600">
          Admin only
        </span>
      </div>
      <p className="mb-4 text-sm text-slate-500">
        Weighted average cost in AED per product per location; value follows stock through
        the physical, in-transit, and pending buckets. Shipping costs are excluded.
      </p>

      <div className="mb-4 flex w-fit gap-1 rounded-lg border border-slate-200 bg-white p-1 text-sm">
        {reports.map((report) => (
          <button
            key={report.key}
            className={`rounded px-4 py-1.5 font-medium ${
              tab === report.key ? "bg-blue-700 text-white" : "text-slate-600 hover:bg-slate-50"
            }`}
            onClick={() => setTab(report.key)}
          >
            {report.title.replace("Stock Valuation ", "")}
          </button>
        ))}
      </div>

      {error && <p className="mb-3 text-sm text-red-600">{error}</p>}
      {selected && <ReportView report={selected} />}
    </div>
  );
}
