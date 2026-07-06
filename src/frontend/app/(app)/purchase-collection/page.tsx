"use client";

import { useCallback, useEffect, useState } from "react";

import { api, errorMessage } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { canWrite } from "@/lib/permissions";

interface PendingLine {
  id: number;
  purchase: number;
  invoice_no: string;
  purchase_date: string;
  location: number;
  location_name: string;
  supplier_name: string;
  product_name: string;
  quantity: string;
  collected: string;
  pending: string;
  currency_code: string;
  unit_price: string;
}

interface ListResponse {
  count: number;
  results: PendingLine[];
}

interface Option {
  id: number;
  name: string;
}

export default function PurchaseCollectionPage() {
  const user = useAuth();
  const writable = canWrite(user?.role, "purchases");

  const [rows, setRows] = useState<PendingLine[]>([]);
  const [count, setCount] = useState(0);
  const [locations, setLocations] = useState<Option[]>([]);
  const [locationFilter, setLocationFilter] = useState("");
  const [quantities, setQuantities] = useState<Record<number, string>>({});
  const [collectionDate, setCollectionDate] = useState(
    new Date().toISOString().slice(0, 10),
  );
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [busyLine, setBusyLine] = useState<number | null>(null);

  const load = useCallback(async () => {
    const query = locationFilter ? `?location=${locationFilter}` : "";
    const data = await api<ListResponse>(`/api/v1/purchases/pending-lines/${query}`);
    setRows(data.results);
    setCount(data.count);
  }, [locationFilter]);

  useEffect(() => {
    load().catch((err) => setError(errorMessage(err)));
  }, [load]);

  useEffect(() => {
    api<{ results: Option[] }>("/api/v1/locations/?can_purchase=true")
      .then((data) => setLocations(data.results))
      .catch(() => undefined);
  }, []);

  async function collect(line: PendingLine, quantity: string) {
    setError("");
    setNotice("");
    setBusyLine(line.id);
    try {
      await api(`/api/v1/purchases/${line.purchase}/collections/`, {
        method: "POST",
        body: {
          collection_date: collectionDate,
          lines: [{ purchase_line: line.id, quantity }],
        },
      });
      setNotice(`Collected ${quantity} × ${line.product_name} (${line.invoice_no}).`);
      setQuantities((prev) => ({ ...prev, [line.id]: "" }));
      await load();
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setBusyLine(null);
    }
  }

  return (
    <div>
      <div className="mb-4 flex flex-wrap items-center gap-3">
        <h1 className="text-xl font-semibold">Purchase Collection / Pending</h1>
        <span className="text-sm text-slate-500">{count} pending lines</span>
        <div className="ml-auto flex items-center gap-2 text-sm">
          <label className="flex items-center gap-2">
            <span className="text-slate-600">Collection date</span>
            <input
              type="date"
              className="rounded border border-slate-300 px-2 py-1.5"
              value={collectionDate}
              onChange={(e) => setCollectionDate(e.target.value)}
            />
          </label>
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
        </div>
      </div>

      {error && <p className="mb-3 text-sm text-red-600">{error}</p>}
      {notice && <p className="mb-3 text-sm text-green-700">{notice}</p>}

      <div className="overflow-x-auto rounded-lg border border-slate-200 bg-white">
        <table className="w-full text-left text-sm">
          <thead className="border-b border-slate-200 bg-slate-50 text-xs uppercase text-slate-500">
            <tr>
              <th className="px-4 py-2.5 font-medium">Invoice</th>
              <th className="px-4 py-2.5 font-medium">Date</th>
              <th className="px-4 py-2.5 font-medium">Location</th>
              <th className="px-4 py-2.5 font-medium">Supplier</th>
              <th className="px-4 py-2.5 font-medium">Product</th>
              <th className="px-4 py-2.5 text-right font-medium">Purchased</th>
              <th className="px-4 py-2.5 text-right font-medium">Collected</th>
              <th className="px-4 py-2.5 text-right font-medium">Pending</th>
              {writable && <th className="px-4 py-2.5 text-right font-medium">Collect</th>}
            </tr>
          </thead>
          <tbody>
            {rows.map((line) => (
              <tr key={line.id} className="border-b border-slate-100 last:border-0">
                <td className="px-4 py-2 font-medium">{line.invoice_no}</td>
                <td className="px-4 py-2">{line.purchase_date}</td>
                <td className="px-4 py-2">{line.location_name}</td>
                <td className="px-4 py-2">{line.supplier_name}</td>
                <td className="px-4 py-2">{line.product_name}</td>
                <td className="px-4 py-2 text-right">{line.quantity}</td>
                <td className="px-4 py-2 text-right">{line.collected}</td>
                <td className="px-4 py-2 text-right font-medium text-amber-700">
                  {line.pending}
                </td>
                {writable && (
                  <td className="px-4 py-2">
                    <div className="flex items-center justify-end gap-2">
                      <input
                        type="number"
                        step="any"
                        min="0"
                        placeholder={line.pending}
                        className="w-24 rounded border border-slate-300 px-2 py-1 text-right text-sm"
                        value={quantities[line.id] ?? ""}
                        onChange={(e) =>
                          setQuantities((prev) => ({
                            ...prev,
                            [line.id]: e.target.value,
                          }))
                        }
                      />
                      <button
                        className="rounded bg-blue-700 px-2.5 py-1 text-xs font-medium text-white hover:bg-blue-800 disabled:opacity-50"
                        disabled={busyLine === line.id}
                        onClick={() =>
                          collect(line, quantities[line.id] || line.pending)
                        }
                      >
                        {busyLine === line.id ? "…" : "Collect"}
                      </button>
                    </div>
                  </td>
                )}
              </tr>
            ))}
            {rows.length === 0 && (
              <tr>
                <td className="px-4 py-6 text-center text-slate-400" colSpan={9}>
                  Nothing pending — all purchased stock has been collected.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
