"use client";

import { Fragment, useCallback, useEffect, useState } from "react";

import { api, ApiError, errorMessage } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { canWrite } from "@/lib/permissions";

interface Option {
  id: number;
  name?: string;
}

interface LineForm {
  id?: number;
  product: string;
  quantity: string;
  unit_price: string;
  notes: string;
}

interface SaleLine {
  id: number;
  product: number;
  product_name: string;
  quantity: string;
  unit_price: string | null;
  notes: string;
}

interface Sale {
  id: number;
  sale_no: string;
  sale_date: string;
  location: number;
  location_name: string;
  customer: number;
  customer_name: string;
  notes: string;
  lines: SaleLine[];
  created_by_username: string | null;
}

interface ListResponse {
  count: number;
  results: Sale[];
  totals?: Record<string, string>;
}

const emptyLine = (): LineForm => ({ product: "", quantity: "", unit_price: "", notes: "" });

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

export default function SalesPage() {
  const user = useAuth();
  const writable = canWrite(user?.role, "sales");

  const [rows, setRows] = useState<Sale[]>([]);
  const [count, setCount] = useState(0);
  const [totals, setTotals] = useState<Record<string, string>>({});
  const [search, setSearch] = useState("");
  const [expanded, setExpanded] = useState<number | null>(null);
  const [error, setError] = useState("");

  const [showForm, setShowForm] = useState(false);
  const [editing, setEditing] = useState<Sale | null>(null);
  const [header, setHeader] = useState({
    sale_date: "",
    location: "",
    customer: "",
    notes: "",
  });
  const [lines, setLines] = useState<LineForm[]>([emptyLine()]);
  const [formError, setFormError] = useState("");
  const [saving, setSaving] = useState(false);

  const [products, setProducts] = useState<Option[]>([]);
  const [locations, setLocations] = useState<Option[]>([]);
  const [customers, setCustomers] = useState<Option[]>([]);

  const load = useCallback(async () => {
    const query = search ? `?search=${encodeURIComponent(search)}` : "";
    const data = await api<ListResponse>(`/api/v1/sales/${query}`);
    setRows(data.results);
    setCount(data.count);
    setTotals(data.totals ?? {});
  }, [search]);

  useEffect(() => {
    load().catch((err) => setError(errorMessage(err)));
  }, [load]);

  useEffect(() => {
    const fetchAll = async (path: string) =>
      (await api<{ results: Option[] }>(path)).results;
    fetchAll("/api/v1/products/?is_active=true").then(setProducts).catch(() => undefined);
    // Only Dubai and Karachi may sell (FR-068); the server enforces this too.
    fetchAll("/api/v1/locations/?is_sales_location=true&is_active=true")
      .then(setLocations)
      .catch(() => undefined);
    fetchAll("/api/v1/customers/?is_active=true").then(setCustomers).catch(() => undefined);
  }, []);

  function openCreate() {
    setEditing(null);
    setHeader({
      sale_date: new Date().toISOString().slice(0, 10),
      location: "",
      customer: "",
      notes: "",
    });
    setLines([emptyLine()]);
    setFormError("");
    setShowForm(true);
  }

  function openEdit(sale: Sale) {
    setEditing(sale);
    setHeader({
      sale_date: sale.sale_date,
      location: String(sale.location),
      customer: String(sale.customer),
      notes: sale.notes,
    });
    setLines(
      sale.lines.map((line) => ({
        id: line.id,
        product: String(line.product),
        quantity: line.quantity,
        unit_price: line.unit_price ?? "",
        notes: line.notes,
      })),
    );
    setFormError("");
    setShowForm(true);
  }

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    setSaving(true);
    setFormError("");
    const payload = {
      ...header,
      location: Number(header.location),
      customer: Number(header.customer),
      lines: lines.map((line) => ({
        ...(line.id !== undefined ? { id: line.id } : {}),
        product: Number(line.product),
        quantity: line.quantity,
        ...(line.unit_price !== "" ? { unit_price: line.unit_price } : { unit_price: null }),
        notes: line.notes,
      })),
    };
    try {
      if (editing) {
        await withNegativeConfirm(
          `/api/v1/sales/${editing.id}/`,
          { method: "PUT", body: payload },
          "This change takes stock negative. Save anyway?",
        );
      } else {
        await withNegativeConfirm(
          "/api/v1/sales/",
          { method: "POST", body: payload },
          "This sale takes stock negative. Record it anyway?",
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

  async function remove(sale: Sale) {
    if (
      !window.confirm(
        `Delete sale ${sale.sale_no}? Sold stock returns to ${sale.location_name}; the record stays traceable in the ledger and audit history.`,
      )
    )
      return;
    try {
      await api(`/api/v1/sales/${sale.id}/`, { method: "DELETE" });
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
        <h1 className="text-xl font-semibold">Sales</h1>
        <span className="text-sm text-slate-500">{count} sales</span>
        <div className="ml-auto flex items-center gap-2">
          <input
            className="rounded border border-slate-300 px-3 py-1.5 text-sm"
            placeholder="Search sale #, product, customer…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
          {writable && (
            <button
              className="rounded bg-blue-700 px-3 py-1.5 text-sm font-medium text-white hover:bg-blue-800"
              onClick={openCreate}
            >
              New Sale
            </button>
          )}
        </div>
      </div>

      <div className="mb-4 grid grid-cols-2 gap-3 sm:grid-cols-3">
        {[
          ["Total quantity", totals.total_quantity],
          ["Sale value (reference)", totals.total_sale_value],
        ].map(([label, value]) => (
          <div key={label} className="rounded-lg border border-slate-200 bg-white px-4 py-3">
            <div className="text-xs uppercase text-slate-500">{label}</div>
            <div className="text-lg font-semibold">{value ?? "—"}</div>
          </div>
        ))}
      </div>

      {error && <p className="mb-3 text-sm text-red-600">{error}</p>}

      <div className="overflow-x-auto rounded-lg border border-slate-200 bg-white">
        <table className="w-full text-left text-sm">
          <thead className="border-b border-slate-200 bg-slate-50 text-xs uppercase text-slate-500">
            <tr>
              <th className="px-4 py-2.5 font-medium">Sale #</th>
              <th className="px-4 py-2.5 font-medium">Date</th>
              <th className="px-4 py-2.5 font-medium">Location</th>
              <th className="px-4 py-2.5 font-medium">Customer</th>
              <th className="px-4 py-2.5 font-medium">Lines</th>
              <th className="px-4 py-2.5 font-medium">By</th>
              <th className="px-4 py-2.5" />
            </tr>
          </thead>
          <tbody>
            {rows.map((sale) => (
              <Fragment key={sale.id}>
                <tr
                  className="cursor-pointer border-b border-slate-100 last:border-0 hover:bg-slate-50"
                  onClick={() => setExpanded(expanded === sale.id ? null : sale.id)}
                >
                  <td className="px-4 py-2 font-medium">{sale.sale_no}</td>
                  <td className="px-4 py-2">{sale.sale_date}</td>
                  <td className="px-4 py-2">{sale.location_name}</td>
                  <td className="px-4 py-2">{sale.customer_name}</td>
                  <td className="px-4 py-2">{sale.lines.length}</td>
                  <td className="px-4 py-2">{sale.created_by_username ?? "—"}</td>
                  <td className="px-4 py-2 text-right whitespace-nowrap">
                    {writable && (
                      <>
                        <button
                          className="text-blue-700 hover:underline"
                          onClick={(e) => {
                            e.stopPropagation();
                            openEdit(sale);
                          }}
                        >
                          Edit
                        </button>
                        <button
                          className="ml-3 text-red-600 hover:underline"
                          onClick={(e) => {
                            e.stopPropagation();
                            remove(sale);
                          }}
                        >
                          Delete
                        </button>
                      </>
                    )}
                  </td>
                </tr>
                {expanded === sale.id && (
                  <tr className="border-b border-slate-100">
                    <td colSpan={7} className="bg-slate-50 px-6 py-3">
                      <table className="w-full text-xs">
                        <thead className="text-slate-500">
                          <tr>
                            <th className="py-1 pr-3 text-left font-medium">Product</th>
                            <th className="py-1 pr-3 text-right font-medium">Qty</th>
                            <th className="py-1 pr-3 text-right font-medium">
                              Sale price (ref)
                            </th>
                            <th className="py-1 text-left font-medium">Notes</th>
                          </tr>
                        </thead>
                        <tbody>
                          {sale.lines.map((line) => (
                            <tr key={line.id} className="border-t border-slate-200">
                              <td className="py-1.5 pr-3">{line.product_name}</td>
                              <td className="py-1.5 pr-3 text-right">{line.quantity}</td>
                              <td className="py-1.5 pr-3 text-right">
                                {line.unit_price ?? "—"}
                              </td>
                              <td className="py-1.5">{line.notes}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </td>
                  </tr>
                )}
              </Fragment>
            ))}
            {rows.length === 0 && (
              <tr>
                <td className="px-4 py-6 text-center text-slate-400" colSpan={7}>
                  No sales
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
            className="max-h-full w-full max-w-3xl overflow-y-auto rounded-lg bg-white p-6 shadow-xl"
          >
            <h2 className="mb-4 text-lg font-semibold">
              {editing ? `Edit ${editing.sale_no}` : "New Sale"}
            </h2>

            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
              <label className="block text-sm">
                <span className="mb-1 block font-medium text-slate-700">
                  Sale date <span className="text-red-500">*</span>
                </span>
                <input
                  className={inputCls}
                  type="date"
                  required
                  value={header.sale_date}
                  onChange={(e) => setHeader({ ...header, sale_date: e.target.value })}
                />
              </label>
              <label className="block text-sm">
                <span className="mb-1 block font-medium text-slate-700">
                  Location <span className="text-red-500">*</span>
                </span>
                <select
                  className={inputCls}
                  required
                  disabled={Boolean(editing)}
                  value={header.location}
                  onChange={(e) => setHeader({ ...header, location: e.target.value })}
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
                  Customer <span className="text-red-500">*</span>
                </span>
                <select
                  className={inputCls}
                  required
                  value={header.customer}
                  onChange={(e) => setHeader({ ...header, customer: e.target.value })}
                >
                  <option value="">— select —</option>
                  {customers.map((customer) => (
                    <option key={customer.id} value={customer.id}>
                      {customer.name}
                    </option>
                  ))}
                </select>
              </label>
            </div>

            <div className="mt-5">
              <div className="mb-2 flex items-center justify-between">
                <h3 className="text-sm font-semibold text-slate-700">Product lines</h3>
                <button
                  type="button"
                  className="text-sm text-blue-700 hover:underline"
                  onClick={() => setLines([...lines, emptyLine()])}
                >
                  + Add line
                </button>
              </div>
              <div className="space-y-3">
                {lines.map((line, index) => (
                  <div
                    key={line.id ?? `new-${index}`}
                    className="grid gap-2 rounded border border-slate-200 p-3 sm:grid-cols-2 lg:grid-cols-5"
                  >
                    <label className="block text-xs lg:col-span-2">
                      <span className="mb-1 block font-medium text-slate-600">Product *</span>
                      <select
                        className={inputCls}
                        required
                        value={line.product}
                        onChange={(e) => {
                          const next = [...lines];
                          next[index] = { ...line, product: e.target.value };
                          setLines(next);
                        }}
                      >
                        <option value="">— select —</option>
                        {products.map((product) => (
                          <option key={product.id} value={product.id}>
                            {product.name}
                          </option>
                        ))}
                      </select>
                    </label>
                    <label className="block text-xs">
                      <span className="mb-1 block font-medium text-slate-600">Qty *</span>
                      <input
                        className={inputCls}
                        type="number"
                        step="any"
                        min="0"
                        required
                        value={line.quantity}
                        onChange={(e) => {
                          const next = [...lines];
                          next[index] = { ...line, quantity: e.target.value };
                          setLines(next);
                        }}
                      />
                    </label>
                    <label className="block text-xs">
                      <span className="mb-1 block font-medium text-slate-600">
                        Sale price (optional)
                      </span>
                      <input
                        className={inputCls}
                        type="number"
                        step="any"
                        min="0"
                        placeholder="reference only"
                        value={line.unit_price}
                        onChange={(e) => {
                          const next = [...lines];
                          next[index] = { ...line, unit_price: e.target.value };
                          setLines(next);
                        }}
                      />
                    </label>
                    <div className="flex items-end justify-end pb-1">
                      {lines.length > 1 && (
                        <button
                          type="button"
                          className="text-xs text-red-600 hover:underline"
                          onClick={() => setLines(lines.filter((_, i) => i !== index))}
                        >
                          Remove
                        </button>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>

            <label className="mt-4 block text-sm">
              <span className="mb-1 block font-medium text-slate-700">Notes</span>
              <textarea
                className={inputCls}
                rows={2}
                value={header.notes}
                onChange={(e) => setHeader({ ...header, notes: e.target.value })}
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
