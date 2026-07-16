"use client";

import { useEffect, useState } from "react";

import ReportView, { type ReportMeta } from "@/components/report-view";
import { api, errorMessage } from "@/lib/api";

export default function ReportsPage() {
  const [reports, setReports] = useState<ReportMeta[]>([]);
  const [selectedKey, setSelectedKey] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    api<ReportMeta[]>("/api/v1/reports/")
      .then((body) => {
        // The valuation reports have their own section in the sidebar.
        const catalogue = body.filter((report) => !report.admin_only);
        setReports(catalogue);
        if (catalogue.length > 0) setSelectedKey(catalogue[0].key);
      })
      .catch((err) => setError(errorMessage(err)));
  }, []);

  const selected = reports.find((report) => report.key === selectedKey);

  return (
    <div>
      <div className="mb-4 flex flex-wrap items-center gap-3">
        <h1 className="text-xl font-semibold">Reports</h1>
        <select
          className="rounded border border-slate-300 bg-white px-3 py-1.5 text-sm"
          value={selectedKey}
          onChange={(e) => setSelectedKey(e.target.value)}
        >
          {reports.map((report) => (
            <option key={report.key} value={report.key}>
              {report.title}
            </option>
          ))}
        </select>
        {selected && <span className="text-sm text-slate-500">{selected.description}</span>}
      </div>

      {error && <p className="mb-3 text-sm text-red-600">{error}</p>}
      {selected && <ReportView report={selected} />}
    </div>
  );
}
