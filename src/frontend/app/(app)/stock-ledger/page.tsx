"use client";

import { useCallback, useEffect, useState } from "react";

import { api, errorMessage } from "@/lib/api";
import { useAuth } from "@/lib/auth";

interface LedgerEntry {
  id: number;
  txn_at: string;
  txn_type: string;
  source_module: string;
  source_id: number;
  product_name: string;
  location_name: string;
  bucket: string;
  qty_in: string;
  qty_out: string;
  net_qty: string;
  related_location_name: string | null;
  currency: string;
  aed_value: string;
  gst_value: string;
  created_by_username: string | null;
}

interface Balance {
  id: number;
  product_name: string;
  location_name: string;
  bucket: string;
  quantity: string;
  value_aed?: string;
}

interface Option {
  id: number;
  name: string;
}

const BUCKETS = ["PHYSICAL", "PENDING", "IN_TRANSIT"];

const BUCKET_STYLES: Record<string, string> = {
  PHYSICAL: "bg-green-50 text-green-700",
  PENDING: "bg-amber-50 text-amber-700",
  IN_TRANSIT: "bg-blue-50 text-blue-700",
};

function BucketBadge({ bucket }: { bucket: string }) {
  return (
    <span
      className={`inline-block rounded px-2 py-0.5 text-xs font-medium ${
        BUCKET_STYLES[bucket] ?? "bg-slate-100 text-slate-600"
      }`}
    >
      {bucket.replaceAll("_", " ")}
    </span>
  );
}

export default function StockLedgerPage() {
  const user = useAuth();
  const isAdmin = user?.role === "ADMIN";

  const [tab, setTab] = useState<"balances" | "ledger">("balances");
  const [entries, setEntries] = useState<LedgerEntry[]>([]);
  const [balances, setBalances] = useState<Balance[]>([]);
  const [count, setCount] = useState(0);
  const [locations, setLocations] = useState<Option[]>([]);
  const [locationFilter, setLocationFilter] = useState("");
  const [bucketFilter, setBucketFilter] = useState("");
  const [search, setSearch] = useState("");
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    const params = new URLSearchParams();
    if (locationFilter) params.set("location", locationFilter);
    if (bucketFilter) params.set("bucket", bucketFilter);
    if (search) params.set("search", search);
    const query = params.size ? `?${params}` : "";
    if (tab === "ledger") {
      const data = await api<{ count: number; results: LedgerEntry[] }>(
        `/api/v1/stock/ledger/${query}`,
      );
      setEntries(data.results);
      setCount(data.count);
    } else {
      const data = await api<{ count: number; results: Balance[] }>(
        `/api/v1/stock/balances/${query}`,
      );
      setBalances(data.results);
      setCount(data.count);
    }
  }, [tab, locationFilter, bucketFilter, search]);

  useEffect(() => {
    load().catch((err) => setError(errorMessage(err)));
  }, [load]);

  useEffect(() => {
    api<{ results: Option[] }>("/api/v1/locations/")
      .then((data) => setLocations(data.results))
      .catch(() => undefined);
  }, []);

  return (
    <div>
      <div className="mb-4 flex flex-wrap items-center gap-3">
        <h1 className="text-xl font-semibold">Stock Ledger</h1>
        <span className="text-sm text-slate-500">{count} rows</span>
        <div className="ml-auto flex items-center gap-2 text-sm">
          <input
            className="rounded border border-slate-300 px-3 py-1.5"
            placeholder="Search product…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
          <select
            className="rounded border border-slate-300 px-2 py-1.5"
            value={locationFilter}
            onChange={(e) => setLocationFilter(e.target.value)}
          >
            <option value="">All locations</option>
            {locations.map((location) => (
              <option key={location.id} value={location.id}>
                {location.name}
              </option>
            ))}
          </select>
          <select
            className="rounded border border-slate-300 px-2 py-1.5"
            value={bucketFilter}
            onChange={(e) => setBucketFilter(e.target.value)}
          >
            <option value="">All buckets</option>
            {BUCKETS.map((bucket) => (
              <option key={bucket} value={bucket}>
                {bucket.replaceAll("_", " ")}
              </option>
            ))}
          </select>
        </div>
      </div>

      <div className="mb-4 flex gap-1 rounded-lg border border-slate-200 bg-white p-1 text-sm w-fit">
        {(["balances", "ledger"] as const).map((key) => (
          <button
            key={key}
            className={`rounded px-4 py-1.5 font-medium ${
              tab === key ? "bg-blue-700 text-white" : "text-slate-600 hover:bg-slate-50"
            }`}
            onClick={() => setTab(key)}
          >
            {key === "balances" ? "Current Balances" : "Movement History"}
          </button>
        ))}
      </div>

      {error && <p className="mb-3 text-sm text-red-600">{error}</p>}

      {tab === "balances" ? (
        <div className="overflow-x-auto rounded-lg border border-slate-200 bg-white">
          <table className="w-full text-left text-sm">
            <thead className="border-b border-slate-200 bg-slate-50 text-xs uppercase text-slate-500">
              <tr>
                <th className="px-4 py-2.5 font-medium">Product</th>
                <th className="px-4 py-2.5 font-medium">Location</th>
                <th className="px-4 py-2.5 font-medium">Bucket</th>
                <th className="px-4 py-2.5 text-right font-medium">Quantity</th>
                {isAdmin && <th className="px-4 py-2.5 text-right font-medium">Value (AED)</th>}
              </tr>
            </thead>
            <tbody>
              {balances.map((balance) => (
                <tr key={balance.id} className="border-b border-slate-100 last:border-0">
                  <td className="px-4 py-2">{balance.product_name}</td>
                  <td className="px-4 py-2">{balance.location_name}</td>
                  <td className="px-4 py-2">
                    <BucketBadge bucket={balance.bucket} />
                  </td>
                  <td
                    className={`px-4 py-2 text-right font-medium ${
                      Number(balance.quantity) < 0 ? "text-red-600" : ""
                    }`}
                  >
                    {balance.quantity}
                  </td>
                  {isAdmin && <td className="px-4 py-2 text-right">{balance.value_aed}</td>}
                </tr>
              ))}
              {balances.length === 0 && (
                <tr>
                  <td className="px-4 py-6 text-center text-slate-400" colSpan={5}>
                    No stock movements yet
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      ) : (
        <div className="overflow-x-auto rounded-lg border border-slate-200 bg-white">
          <table className="w-full text-left text-sm">
            <thead className="border-b border-slate-200 bg-slate-50 text-xs uppercase text-slate-500">
              <tr>
                <th className="px-4 py-2.5 font-medium">Date/time</th>
                <th className="px-4 py-2.5 font-medium">Type</th>
                <th className="px-4 py-2.5 font-medium">Source</th>
                <th className="px-4 py-2.5 font-medium">Product</th>
                <th className="px-4 py-2.5 font-medium">Location</th>
                <th className="px-4 py-2.5 font-medium">Bucket</th>
                <th className="px-4 py-2.5 text-right font-medium">In</th>
                <th className="px-4 py-2.5 text-right font-medium">Out</th>
                <th className="px-4 py-2.5 text-right font-medium">AED</th>
                <th className="px-4 py-2.5 font-medium">By</th>
              </tr>
            </thead>
            <tbody>
              {entries.map((entry) => (
                <tr key={entry.id} className="border-b border-slate-100 last:border-0">
                  <td className="px-4 py-2 whitespace-nowrap">
                    {new Date(entry.txn_at).toLocaleString("en-GB", {
                      timeZone: "Asia/Dubai",
                      dateStyle: "short",
                      timeStyle: "short",
                    })}
                  </td>
                  <td className="px-4 py-2 text-xs">{entry.txn_type.replaceAll("_", " ")}</td>
                  <td className="px-4 py-2 text-xs">
                    {entry.source_module}#{entry.source_id}
                  </td>
                  <td className="px-4 py-2">{entry.product_name}</td>
                  <td className="px-4 py-2">{entry.location_name}</td>
                  <td className="px-4 py-2">
                    <BucketBadge bucket={entry.bucket} />
                  </td>
                  <td className="px-4 py-2 text-right text-green-700">
                    {Number(entry.qty_in) > 0 ? entry.qty_in : ""}
                  </td>
                  <td className="px-4 py-2 text-right text-red-600">
                    {Number(entry.qty_out) > 0 ? entry.qty_out : ""}
                  </td>
                  <td className="px-4 py-2 text-right">{entry.aed_value}</td>
                  <td className="px-4 py-2">{entry.created_by_username ?? "—"}</td>
                </tr>
              ))}
              {entries.length === 0 && (
                <tr>
                  <td className="px-4 py-6 text-center text-slate-400" colSpan={10}>
                    No ledger entries
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
