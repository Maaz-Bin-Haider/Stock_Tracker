"use client";

import { useEffect, useState } from "react";

import ReportView, { type ReportMeta } from "@/components/report-view";
import { api, errorMessage } from "@/lib/api";

interface ExportJobRow {
  id: number;
  report_title: string;
  format: string;
  status: string;
  created_at: string;
  download_url: string | null;
}

function RecentExports() {
  const [open, setOpen] = useState(false);
  const [jobs, setJobs] = useState<ExportJobRow[]>([]);

  useEffect(() => {
    if (!open) return;
    api<{ results: ExportJobRow[] }>("/api/v1/reports/exports/")
      .then((data) => setJobs(data.results.slice(0, 10)))
      .catch(() => undefined);
  }, [open]);

  return (
    <div className="mt-8 border-t border-edge pt-4">
      <button className="text-sm text-primary hover:underline" onClick={() => setOpen(!open)}>
        {open ? "Hide recent exports" : "Show recent exports"}
      </button>
      {open && (
        <ul className="mt-3 space-y-1 text-sm">
          {jobs.map((job) => (
            <li key={job.id} className="flex flex-wrap items-center gap-2">
              <span>{job.report_title}</span>
              <span className="text-xs text-faint">
                {job.format} · {new Date(job.created_at).toLocaleString("en-GB", {
                  timeZone: "Asia/Dubai",
                  dateStyle: "short",
                  timeStyle: "short",
                })}
              </span>
              {job.download_url ? (
                <a href={job.download_url} className="text-xs text-primary hover:underline">
                  Download
                </a>
              ) : (
                <span className="text-xs text-muted">{job.status}</span>
              )}
            </li>
          ))}
          {jobs.length === 0 && <li className="text-xs text-faint">No exports yet.</li>}
        </ul>
      )}
    </div>
  );
}

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
          className="rounded border border-edge bg-surface px-3 py-1.5 text-sm"
          value={selectedKey}
          onChange={(e) => setSelectedKey(e.target.value)}
        >
          {reports.map((report) => (
            <option key={report.key} value={report.key}>
              {report.title}
            </option>
          ))}
        </select>
        {selected && <span className="text-sm text-muted">{selected.description}</span>}
      </div>

      {error && <p className="mb-3 text-sm text-danger">{error}</p>}
      {selected && <ReportView report={selected} />}
      <RecentExports />
    </div>
  );
}
