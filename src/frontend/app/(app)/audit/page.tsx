"use client";

import { useCallback, useEffect, useState } from "react";

import { api, errorMessage } from "@/lib/api";

interface AuditRow {
  id: number;
  user_username: string;
  action: string;
  module: string;
  record_id: number | null;
  record_repr: string;
  before_values: unknown;
  after_values: unknown;
  ip_address: string | null;
  created_at: string;
}

export default function AuditPage() {
  const [rows, setRows] = useState<AuditRow[]>([]);
  const [count, setCount] = useState(0);
  const [search, setSearch] = useState("");
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    const query = search ? `?search=${encodeURIComponent(search)}` : "";
    const data = await api<{ count: number; results: AuditRow[] }>(`/api/v1/audit/${query}`);
    setRows(data.results);
    setCount(data.count);
  }, [search]);

  useEffect(() => {
    load().catch((err) => setError(errorMessage(err)));
  }, [load]);

  return (
    <div>
      <div className="mb-4 flex flex-wrap items-center gap-3">
        <h1 className="text-xl font-semibold">Audit Activity</h1>
        <span className="text-sm text-slate-500">{count} records</span>
        <input
          className="ml-auto rounded border border-slate-300 px-3 py-1.5 text-sm"
          placeholder="Search…"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
      </div>

      {error && <p className="mb-3 text-sm text-red-600">{error}</p>}

      <div className="overflow-x-auto rounded-lg border border-slate-200 bg-white">
        <table className="w-full text-left text-sm">
          <thead className="border-b border-slate-200 bg-slate-50 text-xs uppercase text-slate-500">
            <tr>
              <th className="px-4 py-2.5 font-medium">When</th>
              <th className="px-4 py-2.5 font-medium">User</th>
              <th className="px-4 py-2.5 font-medium">Action</th>
              <th className="px-4 py-2.5 font-medium">Module</th>
              <th className="px-4 py-2.5 font-medium">Record</th>
              <th className="px-4 py-2.5 font-medium">Details</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr key={row.id} className="border-b border-slate-100 align-top last:border-0">
                <td className="whitespace-nowrap px-4 py-2 text-slate-500">
                  {new Date(row.created_at).toLocaleString()}
                </td>
                <td className="px-4 py-2">{row.user_username || "—"}</td>
                <td className="px-4 py-2">
                  <span className="rounded bg-slate-100 px-2 py-0.5 text-xs font-medium">
                    {row.action}
                  </span>
                </td>
                <td className="px-4 py-2">{row.module || "—"}</td>
                <td className="px-4 py-2">{row.record_repr || row.record_id || "—"}</td>
                <td className="px-4 py-2">
                  {row.before_values || row.after_values ? (
                    <details>
                      <summary className="cursor-pointer text-xs text-blue-700">
                        before / after
                      </summary>
                      <pre className="mt-1 max-w-md overflow-x-auto rounded bg-slate-50 p-2 text-xs">
                        {JSON.stringify(
                          { before: row.before_values, after: row.after_values },
                          null,
                          2,
                        )}
                      </pre>
                    </details>
                  ) : (
                    "—"
                  )}
                </td>
              </tr>
            ))}
            {rows.length === 0 && (
              <tr>
                <td className="px-4 py-6 text-center text-slate-400" colSpan={6}>
                  No records
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
