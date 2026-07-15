"use client";

import { useCallback, useEffect, useState } from "react";

import { api, ApiError, errorMessage } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { canWrite } from "@/lib/permissions";

interface Option {
  id: number;
  name?: string;
}

interface Adjustment {
  id: number;
  adjustment_date: string;
  location: number;
  location_name: string;
  product: number;
  product_name: string;
  adjustment_type: "INCREASE" | "DECREASE";
  quantity: string;
  reason: string;
  notes: string;
  created_by_username: string | null;
}

interface ListResponse {
  count: number;
  results: Adjustment[];
}

/** Retry a write with ?confirm_negative=true after the user confirms. */
async function withNegativeConfirm(
  path: string,
  options: { method: string; body?: unknown },
  message: string,
) {
  try {
    await api(path, options);
  } catch (err) {
    if (
      err instanceof ApiError &&
      typeof err.body === "object" &&
      err.body !== null &&
      (err.body as { code?: string[] | string }).code
        ?.toString()
        .includes("negative_stock_confirmation_required") &&
      window.confirm(message)
    ) {
      const sep = path.includes("?") ? "&" : "?";
      await api(`${path}${sep}confirm_negative=true`, options);
    } else {
      throw err;
    }
  }
}

export default function StockAdjustmentsPage() {
  const user = useAuth();
  const writable = canWrite(user?.role, "stock-adjustments");

  const [rows, setRows] = useState<Adjustment[]>([]);
  const [count, setCount] = useState(0);
  const [search, setSearch] = useState("");
  const [error, setError] = useState("");

  const [showForm, setShowForm] = useState(false);
  const [editing, setEditing] = useState<Adjustment | null>(null);
  const [form, setForm] = useState({
    adjustment_date: "",
    location: "",
    product: "",
    adjustment_type: "DECREASE",
    quantity: "",
    reason: "",
    notes: "",
  });
  const [formError, setFormError] = useState("");
  const [saving, setSaving] = useState(false);

  const [products, setProducts] = useState<Option[]>([]);
  const [locations, setLocations] = useState<Option[]>([]);

  const load = useCallback(async () => {
    const query = search ? `?search=${encodeURIComponent(search)}` : "";
    const data = await api<ListResponse>(`/api/v1/stock-adjustments/${query}`);
    setRows(data.results);
    setCount(data.count);
  }, [search]);

  useEffect(() => {
    load().catch((err) => setError(errorMessage(err)));
  }, [load]);

  useEffect(() => {
    const fetchAll = async (path: string) =>
      (await api<{ results: Option[] }>(path)).results;
    fetchAll("/api/v1/products/?is_active=true").then(setProducts).catch(() => undefined);
    fetchAll("/api/v1/locations/?is_active=true").then(setLocations).catch(() => undefined);
  }, []);

  function openCreate() {
    setEditing(null);
    setForm({
      adjustment_date: new Date().toISOString().slice(0, 10),
      location: "",
      product: "",
      adjustment_type: "DECREASE",
      quantity: "",
      reason: "",
      notes: "",
    });
    setFormError("");
    setShowForm(true);
  }

  function openEdit(adjustment: Adjustment) {
    setEditing(adjustment);
    setForm({
      adjustment_date: adjustment.adjustment_date,
      location: String(adjustment.location),
      product: String(adjustment.product),
      adjustment_type: adjustment.adjustment_type,
      quantity: adjustment.quantity,
      reason: adjustment.reason,
      notes: adjustment.notes,
    });
    setFormError("");
    setShowForm(true);
  }

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    setSaving(true);
    setFormError("");
    const payload = {
      ...form,
      location: Number(form.location),
      product: Number(form.product),
    };
    try {
      if (editing) {
        await withNegativeConfirm(
          `/api/v1/stock-adjustments/${editing.id}/`,
          { method: "PUT", body: payload },
          "This change takes stock negative. Save anyway?",
        );
      } else {
        await withNegativeConfirm(
          "/api/v1/stock-adjustments/",
          { method: "POST", body: payload },
          "This adjustment takes stock negative. Record it anyway?",
        );
      }
      setShowForm(false);
      await load();
    } catch (err) {
      setFormError(errorMessage(err));
    } finally {
      setSaving(false);
    }
  }

  async function remove(adjustment: Adjustment) {
    if (
      !window.confirm(
        "Delete this adjustment? Its stock effect will be reversed; the record stays traceable in the ledger and audit history.",
      )
    )
      return;
    try {
      await withNegativeConfirm(
        `/api/v1/stock-adjustments/${adjustment.id}/`,
        { method: "DELETE" },
        "Reversing this adjustment takes stock negative. Continue?",
      );
      await load();
    } catch (err) {
      setError(errorMessage(err));
    }
  }

  const inputCls =
    "w-full rounded border border-slate-300 px-2 py-1.5 text-sm focus:border-blue-500 focus:outline-none";

  return (
    <div>
      <div className="mb-4 flex flex-wrap items-center gap-3">
        <h1 className="text-xl font-semibold">Stock Adjustments</h1>
        <span className="text-sm text-slate-500">{count} adjustments</span>
        <div className="ml-auto flex items-center gap-2">
          <input
            className="rounded border border-slate-300 px-3 py-1.5 text-sm"
            placeholder="Search reason, product…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
          {writable && (
            <button
              className="rounded bg-blue-700 px-3 py-1.5 text-sm font-medium text-white hover:bg-blue-800"
              onClick={openCreate}
            >
              New Adjustment
            </button>
          )}
        </div>
      </div>

      {error && <p className="mb-3 text-sm text-red-600">{error}</p>}

      <div className="overflow-x-auto rounded-lg border border-slate-200 bg-white">
        <table className="w-full text-left text-sm">
          <thead className="border-b border-slate-200 bg-slate-50 text-xs uppercase text-slate-500">
            <tr>
              <th className="px-4 py-2.5 font-medium">Date</th>
              <th className="px-4 py-2.5 font-medium">Location</th>
              <th className="px-4 py-2.5 font-medium">Product</th>
              <th className="px-4 py-2.5 font-medium">Type</th>
              <th className="px-4 py-2.5 text-right font-medium">Qty</th>
              <th className="px-4 py-2.5 font-medium">Reason</th>
              <th className="px-4 py-2.5 font-medium">By</th>
              <th className="px-4 py-2.5" />
            </tr>
          </thead>
          <tbody>
            {rows.map((adjustment) => (
              <tr
                key={adjustment.id}
                className="border-b border-slate-100 last:border-0 hover:bg-slate-50"
              >
                <td className="px-4 py-2">{adjustment.adjustment_date}</td>
                <td className="px-4 py-2">{adjustment.location_name}</td>
                <td className="px-4 py-2">{adjustment.product_name}</td>
                <td className="px-4 py-2">
                  <span
                    className={`inline-block rounded px-2 py-0.5 text-xs font-medium ${
                      adjustment.adjustment_type === "INCREASE"
                        ? "bg-green-50 text-green-700"
                        : "bg-amber-50 text-amber-700"
                    }`}
                  >
                    {adjustment.adjustment_type === "INCREASE" ? "+ increase" : "− decrease"}
                  </span>
                </td>
                <td className="px-4 py-2 text-right">{adjustment.quantity}</td>
                <td className="px-4 py-2">{adjustment.reason}</td>
                <td className="px-4 py-2">{adjustment.created_by_username ?? "—"}</td>
                <td className="px-4 py-2 text-right whitespace-nowrap">
                  {writable && (
                    <>
                      <button
                        className="text-blue-700 hover:underline"
                        onClick={() => openEdit(adjustment)}
                      >
                        Edit
                      </button>
                      <button
                        className="ml-3 text-red-600 hover:underline"
                        onClick={() => remove(adjustment)}
                      >
                        Delete
                      </button>
                    </>
                  )}
                </td>
              </tr>
            ))}
            {rows.length === 0 && (
              <tr>
                <td className="px-4 py-6 text-center text-slate-400" colSpan={8}>
                  No stock adjustments
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      {showForm && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
          <form
            onSubmit={submit}
            className="max-h-full w-full max-w-2xl overflow-y-auto rounded-lg bg-white p-6 shadow-xl"
          >
            <h2 className="mb-4 text-lg font-semibold">
              {editing ? "Edit Adjustment" : "New Stock Adjustment"}
            </h2>

            <div className="grid gap-3 sm:grid-cols-2">
              <label className="block text-sm">
                <span className="mb-1 block font-medium text-slate-700">
                  Date <span className="text-red-500">*</span>
                </span>
                <input
                  className={inputCls}
                  type="date"
                  required
                  value={form.adjustment_date}
                  onChange={(e) => setForm({ ...form, adjustment_date: e.target.value })}
                />
              </label>
              <label className="block text-sm">
                <span className="mb-1 block font-medium text-slate-700">
                  Location <span className="text-red-500">*</span>
                </span>
                <select
                  className={inputCls}
                  required
                  value={form.location}
                  onChange={(e) => setForm({ ...form, location: e.target.value })}
                >
                  <option value="">— select —</option>
                  {locations.map((location) => (
                    <option key={location.id} value={location.id}>
                      {location.name}
                    </option>
                  ))}
                </select>
              </label>
              <label className="block text-sm">
                <span className="mb-1 block font-medium text-slate-700">
                  Product <span className="text-red-500">*</span>
                </span>
                <select
                  className={inputCls}
                  required
                  value={form.product}
                  onChange={(e) => setForm({ ...form, product: e.target.value })}
                >
                  <option value="">— select —</option>
                  {products.map((product) => (
                    <option key={product.id} value={product.id}>
                      {product.name}
                    </option>
                  ))}
                </select>
              </label>
              <label className="block text-sm">
                <span className="mb-1 block font-medium text-slate-700">
                  Type <span className="text-red-500">*</span>
                </span>
                <select
                  className={inputCls}
                  required
                  value={form.adjustment_type}
                  onChange={(e) => setForm({ ...form, adjustment_type: e.target.value })}
                >
                  <option value="DECREASE">Decrease (damaged, lost, count down)</option>
                  <option value="INCREASE">Increase (extra found, count up)</option>
                </select>
              </label>
              <label className="block text-sm">
                <span className="mb-1 block font-medium text-slate-700">
                  Quantity <span className="text-red-500">*</span>
                </span>
                <input
                  className={inputCls}
                  type="number"
                  step="any"
                  min="0"
                  required
                  value={form.quantity}
                  onChange={(e) => setForm({ ...form, quantity: e.target.value })}
                />
              </label>
              <label className="block text-sm">
                <span className="mb-1 block font-medium text-slate-700">
                  Reason <span className="text-red-500">*</span>
                </span>
                <input
                  className={inputCls}
                  required
                  placeholder="e.g. damaged during stock count"
                  value={form.reason}
                  onChange={(e) => setForm({ ...form, reason: e.target.value })}
                />
              </label>
            </div>

            <label className="mt-4 block text-sm">
              <span className="mb-1 block font-medium text-slate-700">Notes</span>
              <textarea
                className={inputCls}
                rows={2}
                value={form.notes}
                onChange={(e) => setForm({ ...form, notes: e.target.value })}
              />
            </label>

            {formError && <p className="mt-3 text-sm text-red-600">{formError}</p>}
            <div className="mt-5 flex justify-end gap-2">
              <button
                type="button"
                className="rounded border border-slate-300 px-4 py-1.5 text-sm"
                onClick={() => setShowForm(false)}
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={saving}
                className="rounded bg-blue-700 px-4 py-1.5 text-sm font-medium text-white hover:bg-blue-800 disabled:opacity-50"
              >
                {saving ? "Saving…" : "Save"}
              </button>
            </div>
          </form>
        </div>
      )}
    </div>
  );
}
