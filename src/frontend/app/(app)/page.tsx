"use client";

import { useCallback, useEffect, useState } from "react";

import { formatCell } from "@/components/report-view";
import { api, errorMessage } from "@/lib/api";
import { useAuth } from "@/lib/auth";

interface LocationStock {
  location: string;
  physical: number;
  pending: number;
  in_transit: number;
}

interface DashboardData {
  as_of: string | null;
  business_date: string;
  cards: {
    total_physical: number;
    total_pending: number;
    total_in_transit: number;
    gst_total_aed: number;
    todays_sales: { quantity: number; lines: number };
    sales_locations: { location: string; physical: number; in_transit: number }[];
  };
  stock_by_location: LocationStock[];
}

function Card({ label, value, sub }: { label: string; value: string; sub?: string }) {
  return (
    <div className="rounded-lg border border-edge bg-surface p-4">
      <div className="text-xs font-medium uppercase tracking-wide text-muted">{label}</div>
      <div className="mt-1 text-2xl font-semibold">{value}</div>
      {sub && <div className="mt-0.5 text-xs text-faint">{sub}</div>}
    </div>
  );
}

export default function DashboardPage() {
  const user = useAuth();
  const [data, setData] = useState<DashboardData | null>(null);
  const [cutoff, setCutoff] = useState("");
  const [appliedCutoff, setAppliedCutoff] = useState("");
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    setError("");
    try {
      const query = appliedCutoff ? `?cutoff=${encodeURIComponent(appliedCutoff)}` : "";
      setData(await api<DashboardData>(`/api/v1/reports/dashboard/${query}`));
    } catch (err) {
      setError(errorMessage(err));
    }
  }, [appliedCutoff]);

  useEffect(() => {
    load();
  }, [load]);

  const qty = (value: number) => formatCell(value, "qty");
  const money = (value: number) => formatCell(value, "money");

  return (
    <div>
      <div className="mb-4 flex flex-wrap items-end gap-3">
        <div className="mr-auto">
          <h1 className="text-xl font-semibold">Dashboard</h1>
          <p className="text-sm text-muted">
            Welcome back, <span className="font-medium">{user?.username}</span>
            {data && (
              <>
                {" · "}
                {data.as_of
                  ? `snapshot as of ${formatCell(data.as_of, "datetime")} (Dubai time)`
                  : `live · business date ${formatCell(data.business_date, "date")} (Dubai)`}
              </>
            )}
          </p>
        </div>
        <label className="flex flex-col gap-1 text-xs text-muted">
          Past snapshot (Dubai time)
          <input
            type="datetime-local"
            className="rounded border border-edge bg-surface px-2 py-1.5 text-sm"
            value={cutoff}
            onChange={(e) => setCutoff(e.target.value)}
          />
        </label>
        <button
          className="rounded bg-primary px-3 py-1.5 text-sm font-medium text-on-primary hover:bg-primary-strong disabled:opacity-50"
          disabled={!cutoff}
          onClick={() => setAppliedCutoff(cutoff)}
        >
          View snapshot
        </button>
        {appliedCutoff && (
          <button
            className="rounded px-3 py-1.5 text-sm text-primary hover:underline"
            onClick={() => {
              setCutoff("");
              setAppliedCutoff("");
            }}
          >
            Back to live
          </button>
        )}
      </div>

      {error && <p className="mb-3 text-sm text-danger">{error}</p>}

      {data && (
        <>
          {data.as_of && (
            <div className="mb-4 rounded-lg border border-warning-edge bg-warning-soft px-4 py-2 text-sm text-warning">
              Showing a past snapshot — stock figures are rebuilt from the ledger up to the
              cutoff (FR-096).
            </div>
          )}

          <div className="mb-6 grid grid-cols-2 gap-4 md:grid-cols-3 xl:grid-cols-4">
            <Card label="Total company stock" value={qty(data.cards.total_physical)} sub="physical units" />
            <Card label="Pending stock" value={qty(data.cards.total_pending)} sub="purchased, not collected" />
            <Card label="In-transit stock" value={qty(data.cards.total_in_transit)} sub="shipped, not received" />
            <Card label="GST total" value={`${money(data.cards.gst_total_aed)} AED`} sub="net of refunds" />
            {data.cards.sales_locations.map((card) => (
              <Card
                key={card.location}
                label={`${card.location} stock`}
                value={qty(card.physical)}
                sub={`${qty(card.in_transit)} in transit`}
              />
            ))}
            <Card
              label={data.as_of ? "Sales on snapshot day" : "Today's sales"}
              value={qty(data.cards.todays_sales.quantity)}
              sub={`${data.cards.todays_sales.lines} sale line(s)`}
            />
          </div>

          <h2 className="mb-2 text-sm font-semibold text-ink-2">Stock by location</h2>
          <div className="overflow-x-auto rounded-lg border border-edge bg-surface">
            <table className="w-full text-left text-sm">
              <thead className="border-b border-edge bg-surface-2 text-xs uppercase text-muted">
                <tr>
                  <th className="px-4 py-2.5 font-medium">Location</th>
                  <th className="px-4 py-2.5 text-right font-medium">Physical</th>
                  <th className="px-4 py-2.5 text-right font-medium">Pending</th>
                  <th className="px-4 py-2.5 text-right font-medium">In transit</th>
                </tr>
              </thead>
              <tbody>
                {data.stock_by_location.map((row) => (
                  <tr key={row.location} className="border-b border-edge-2 last:border-0">
                    <td className="px-4 py-2">{row.location}</td>
                    <td className={`px-4 py-2 text-right ${row.physical < 0 ? "font-medium text-danger" : ""}`}>
                      {qty(row.physical)}
                    </td>
                    <td className="px-4 py-2 text-right">{qty(row.pending)}</td>
                    <td className="px-4 py-2 text-right">{qty(row.in_transit)}</td>
                  </tr>
                ))}
                {data.stock_by_location.length === 0 && (
                  <tr>
                    <td className="px-4 py-6 text-center text-faint" colSpan={4}>
                      No stock movements yet
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </>
      )}
    </div>
  );
}
