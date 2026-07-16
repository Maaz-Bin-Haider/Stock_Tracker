"use client";

import { useCallback, useEffect, useRef, useState } from "react";

import { api, errorMessage } from "@/lib/api";

export interface ReportMeta {
  key: string;
  title: string;
  description: string;
  filters: string[];
  admin_only: boolean;
}

interface ReportColumn {
  key: string;
  label: string;
  kind: string;
}

interface ReportSection {
  title: string;
  columns: ReportColumn[];
  rows: Record<string, unknown>[];
  row_count: number;
}

interface ReportData {
  key: string;
  title: string;
  sections: ReportSection[];
  totals: Record<string, unknown>;
  truncated: boolean;
}

interface ExportJob {
  id: number;
  status: "PENDING" | "RUNNING" | "DONE" | "FAILED";
  error: string;
  download_url: string | null;
}

interface Option {
  id: number;
  name?: string;
  username?: string;
  storage_specs?: string;
}

const NUMERIC_KINDS = new Set(["qty", "money", "percent"]);

const SELECT_FILTERS: Record<string, string> = {
  location: "/api/v1/locations/",
  product: "/api/v1/products/",
  category: "/api/v1/categories/",
  supplier: "/api/v1/suppliers/",
  customer: "/api/v1/customers/",
  user: "/api/v1/users/",
};

const ENUM_FILTERS: Record<string, string[]> = {
  bucket: ["PHYSICAL", "PENDING", "IN_TRANSIT"],
  adjustment_type: ["INCREASE", "DECREASE"],
  action: ["CREATE", "UPDATE", "DELETE", "LOGIN", "LOGOUT", "LOGIN_FAILED"],
  txn_type: [
    "PURCHASE_ENTRY",
    "PURCHASE_COLLECTION",
    "PURCHASE_REFUND",
    "SHIPMENT_OUT",
    "SHIPMENT_RECEIPT",
    "SHIPMENT_CANCEL",
    "SALE",
    "ADJUSTMENT",
    "EDIT_REVERSAL",
    "DELETE_REVERSAL",
  ],
};

const FILTER_LABELS: Record<string, string> = {
  date_from: "From date",
  date_to: "To date",
  cutoff: "As of (Dubai time)",
  location: "Location",
  product: "Product",
  category: "Category",
  supplier: "Supplier",
  customer: "Customer",
  status: "Status",
  bucket: "Bucket",
  txn_type: "Transaction type",
  adjustment_type: "Adjustment type",
  action: "Action",
  module: "Module",
  user: "User",
};

export function formatCell(value: unknown, kind: string): string {
  if (value === null || value === undefined || value === "") return "";
  if (kind === "bool") return value ? "Yes" : "";
  if (kind === "money")
    return Number(value).toLocaleString("en-GB", {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    });
  if (kind === "qty" || kind === "percent")
    return Number(value).toLocaleString("en-GB", { maximumFractionDigits: 2 });
  if (kind === "datetime")
    return new Date(String(value)).toLocaleString("en-GB", {
      timeZone: "Asia/Dubai",
      dateStyle: "short",
      timeStyle: "short",
    });
  if (kind === "date") {
    const [year, month, day] = String(value).split("-");
    return day && month ? `${day}/${month}/${year}` : String(value);
  }
  return String(value);
}

function optionLabel(option: Option): string {
  const name = option.name ?? option.username ?? `#${option.id}`;
  return option.storage_specs ? `${name} ${option.storage_specs}` : name;
}

export default function ReportView({ report }: { report: ReportMeta }) {
  const [filters, setFilters] = useState<Record<string, string>>({});
  const [data, setData] = useState<ReportData | null>(null);
  const [options, setOptions] = useState<Record<string, Option[]>>({});
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [exporting, setExporting] = useState<"XLSX" | "PDF" | null>(null);
  const [exportNote, setExportNote] = useState("");
  const pollTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Reset state when switching reports.
  useEffect(() => {
    setFilters({});
    setData(null);
    setError("");
    setExportNote("");
  }, [report.key]);

  useEffect(() => {
    report.filters
      .filter((name) => SELECT_FILTERS[name] && !options[name])
      .forEach((name) => {
        api<{ results: Option[] }>(SELECT_FILTERS[name])
          .then((body) =>
            setOptions((current) => ({ ...current, [name]: body.results })),
          )
          .catch(() => undefined);
      });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [report.key]);

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const params = new URLSearchParams(
        Object.entries(filters).filter(([, value]) => value !== ""),
      );
      const query = params.size ? `?${params}` : "";
      setData(await api<ReportData>(`/api/v1/reports/${report.key}/${query}`));
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setLoading(false);
    }
  }, [report.key, filters]);

  useEffect(() => {
    load();
  }, [load]);

  useEffect(() => () => {
    if (pollTimer.current) clearTimeout(pollTimer.current);
  }, []);

  async function startExport(format: "XLSX" | "PDF") {
    setExporting(format);
    setExportNote("Preparing export…");
    try {
      const job = await api<ExportJob>(`/api/v1/reports/${report.key}/export/`, {
        method: "POST",
        body: { format, filters },
      });
      await pollJob(job.id);
    } catch (err) {
      setExportNote("");
      setError(errorMessage(err));
      setExporting(null);
    }
  }

  async function pollJob(jobId: number, attempt = 0) {
    const job = await api<ExportJob>(`/api/v1/reports/exports/${jobId}/`);
    if (job.status === "DONE" && job.download_url) {
      setExporting(null);
      setExportNote("");
      window.location.assign(job.download_url);
      return;
    }
    if (job.status === "FAILED") {
      setExporting(null);
      setExportNote("");
      setError(`Export failed: ${job.error || "unknown error"}`);
      return;
    }
    if (attempt > 60) {
      setExporting(null);
      setExportNote("Export is still running — check back from the exports list.");
      return;
    }
    setExportNote("Generating file…");
    pollTimer.current = setTimeout(() => pollJob(jobId, attempt + 1), 1500);
  }

  function setFilter(name: string, value: string) {
    setFilters((current) => ({ ...current, [name]: value }));
  }

  function filterControl(name: string) {
    const value = filters[name] ?? "";
    const base = "rounded border border-edge px-2 py-1.5 text-sm bg-surface";
    if (name === "date_from" || name === "date_to") {
      return (
        <input type="date" className={base} value={value}
          onChange={(e) => setFilter(name, e.target.value)} />
      );
    }
    if (name === "cutoff") {
      return (
        <input type="datetime-local" className={base} value={value}
          onChange={(e) => setFilter(name, e.target.value)} />
      );
    }
    if (SELECT_FILTERS[name]) {
      return (
        <select className={base} value={value} onChange={(e) => setFilter(name, e.target.value)}>
          <option value="">All</option>
          {(options[name] ?? []).map((option) => (
            <option key={option.id} value={option.id}>
              {optionLabel(option)}
            </option>
          ))}
        </select>
      );
    }
    if (ENUM_FILTERS[name]) {
      return (
        <select className={base} value={value} onChange={(e) => setFilter(name, e.target.value)}>
          <option value="">All</option>
          {ENUM_FILTERS[name].map((choice) => (
            <option key={choice} value={choice}>
              {choice.replaceAll("_", " ")}
            </option>
          ))}
        </select>
      );
    }
    return (
      <input type="text" className={base} value={value} placeholder="Any"
        onChange={(e) => setFilter(name, e.target.value)} />
    );
  }

  return (
    <div>
      {report.filters.length > 0 && (
        <div className="mb-4 flex flex-wrap items-end gap-3 rounded-lg border border-edge bg-surface p-3">
          {report.filters.map((name) => (
            <label key={name} className="flex flex-col gap-1 text-xs text-muted">
              {FILTER_LABELS[name] ?? name}
              {filterControl(name)}
            </label>
          ))}
          {Object.values(filters).some((value) => value !== "") && (
            <button
              className="rounded px-3 py-1.5 text-sm text-primary hover:underline"
              onClick={() => setFilters({})}
            >
              Clear filters
            </button>
          )}
          <div className="ml-auto flex items-center gap-2">
            {exportNote && <span className="text-xs text-muted">{exportNote}</span>}
            {(["XLSX", "PDF"] as const).map((format) => (
              <button
                key={format}
                disabled={exporting !== null}
                onClick={() => startExport(format)}
                className="rounded border border-edge bg-surface px-3 py-1.5 text-sm font-medium text-ink-2 hover:bg-surface-2 disabled:opacity-50"
              >
                {exporting === format ? "Exporting…" : `Export ${format === "XLSX" ? "Excel" : "PDF"}`}
              </button>
            ))}
          </div>
        </div>
      )}

      {error && <p className="mb-3 text-sm text-danger">{error}</p>}
      {loading && !data && <p className="text-sm text-faint">Loading…</p>}

      {data && Object.keys(data.totals).length > 0 && (
        <div className="mb-4 flex flex-wrap gap-4">
          {Object.entries(data.totals).map(([label, value]) => (
            <div key={label} className="rounded-lg border border-edge bg-surface px-4 py-2">
              <div className="text-xs text-muted">{label}</div>
              <div className="text-base font-semibold">
                {typeof value === "number"
                  ? formatCell(value, Number.isInteger(value) ? "qty" : "money")
                  : String(value)}
              </div>
            </div>
          ))}
        </div>
      )}

      {data?.truncated && (
        <p className="mb-3 text-xs text-warning">
          Showing the first rows only — export to Excel/PDF for the complete filtered dataset.
        </p>
      )}

      {data?.sections.map((section) => (
        <div key={section.title} className="mb-6">
          {data.sections.length > 1 && (
            <h2 className="mb-2 text-sm font-semibold text-ink-2">{section.title}</h2>
          )}
          <div className="overflow-x-auto rounded-lg border border-edge bg-surface">
            <table className="w-full text-left text-sm">
              <thead className="border-b border-edge bg-surface-2 text-xs uppercase text-muted">
                <tr>
                  {section.columns.map((column) => (
                    <th
                      key={column.key}
                      className={`px-3 py-2.5 font-medium ${
                        NUMERIC_KINDS.has(column.kind) ? "text-right" : ""
                      }`}
                    >
                      {column.label}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {section.rows.map((row, index) => (
                  <tr key={index} className="border-b border-edge-2 last:border-0">
                    {section.columns.map((column) => {
                      const raw = row[column.key];
                      const negative =
                        (column.kind === "bool" && column.key === "negative" && raw === true) ||
                        (NUMERIC_KINDS.has(column.kind) && Number(raw) < 0);
                      return (
                        <td
                          key={column.key}
                          className={`px-3 py-2 ${
                            NUMERIC_KINDS.has(column.kind) ? "text-right" : ""
                          } ${negative ? "font-medium text-danger" : ""}`}
                        >
                          {formatCell(raw, column.kind)}
                        </td>
                      );
                    })}
                  </tr>
                ))}
                {section.rows.length === 0 && (
                  <tr>
                    <td
                      className="px-4 py-6 text-center text-faint"
                      colSpan={section.columns.length}
                    >
                      No data for the selected filters
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      ))}
    </div>
  );
}
