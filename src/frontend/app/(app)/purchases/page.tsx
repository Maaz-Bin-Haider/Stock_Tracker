"use client";

import { Fragment, useCallback, useEffect, useState } from "react";

import AttachmentsPanel from "@/components/attachments-panel";
import Pagination from "@/components/pagination";
import { api, errorMessage } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { canWrite } from "@/lib/permissions";

interface Option {
  id: number;
  name?: string;
  code?: string;
}

interface LineForm {
  id?: number;
  product: string;
  quantity: string;
  unit_price: string;
  currency: string;
  exchange_rate: string;
  gst_rate_percent: string;
  collected_qty: string;
  notes: string;
  /** Set for existing lines with collected stock: pricing is locked. */
  collected?: string;
}

interface PurchaseLine {
  id: number;
  product: number;
  product_name: string;
  quantity: string;
  unit_price: string;
  currency: number;
  currency_code: string;
  exchange_rate: string;
  unit_price_aed: string;
  total_value_aed: string;
  gst_rate_percent: string;
  gst_amount: string;
  gst_amount_aed: string;
  collected: string;
  pending: string;
  status: string;
  notes: string;
}

interface Purchase {
  id: number;
  invoice_no: string;
  purchase_date: string;
  location: number;
  location_name: string;
  supplier: number;
  supplier_name: string;
  status: string;
  notes: string;
  lines: PurchaseLine[];
}

interface ListResponse {
  count: number;
  results: Purchase[];
  totals?: Record<string, string>;
}

const emptyLine = (): LineForm => ({
  product: "",
  quantity: "",
  unit_price: "",
  currency: "",
  exchange_rate: "",
  gst_rate_percent: "",
  collected_qty: "",
  notes: "",
});

const STATUS_STYLES: Record<string, string> = {
  PENDING: "bg-warning-soft text-warning",
  PARTIALLY_RECEIVED: "bg-primary-soft text-primary",
  FULLY_COLLECTED: "bg-success-soft text-success",
  CANCELLED: "bg-surface-2 text-muted",
  REFUNDED: "bg-surface-2 text-muted",
};

function StatusBadge({ status }: { status: string }) {
  return (
    <span
      className={`inline-block rounded px-2 py-0.5 text-xs font-medium ${
        STATUS_STYLES[status] ?? "bg-surface-2 text-ink-2"
      }`}
    >
      {status.replaceAll("_", " ")}
    </span>
  );
}

export default function PurchasesPage() {
  const user = useAuth();
  const writable = canWrite(user?.role, "purchases");

  const [rows, setRows] = useState<Purchase[]>([]);
  const [count, setCount] = useState(0);
  const [page, setPage] = useState(1);
  const [totals, setTotals] = useState<Record<string, string>>({});
  const [search, setSearch] = useState("");
  const [expanded, setExpanded] = useState<number | null>(null);
  const [error, setError] = useState("");

  const [showForm, setShowForm] = useState(false);
  const [editing, setEditing] = useState<Purchase | null>(null);
  const [header, setHeader] = useState({
    invoice_no: "",
    purchase_date: "",
    location: "",
    supplier: "",
    notes: "",
  });
  const [lines, setLines] = useState<LineForm[]>([emptyLine()]);
  const [formError, setFormError] = useState("");
  const [saving, setSaving] = useState(false);

  const [products, setProducts] = useState<Option[]>([]);
  const [locations, setLocations] = useState<Option[]>([]);
  const [suppliers, setSuppliers] = useState<Option[]>([]);
  const [currencies, setCurrencies] = useState<Option[]>([]);

  const load = useCallback(async () => {
    const params = new URLSearchParams();
    if (search) params.set("search", search);
    if (page > 1) params.set("page", String(page));
    const query = params.size ? `?${params}` : "";
    const data = await api<ListResponse>(`/api/v1/purchases/${query}`);
    setRows(data.results);
    setCount(data.count);
    setTotals(data.totals ?? {});
  }, [search, page]);

  useEffect(() => {
    load().catch((err) => setError(errorMessage(err)));
  }, [load]);

  useEffect(() => {
    const fetchAll = async (path: string) =>
      (await api<{ results: Option[] }>(path)).results;
    fetchAll("/api/v1/products/?is_active=true").then(setProducts).catch(() => undefined);
    fetchAll("/api/v1/locations/?can_purchase=true&is_active=true")
      .then(setLocations)
      .catch(() => undefined);
    fetchAll("/api/v1/suppliers/?is_active=true").then(setSuppliers).catch(() => undefined);
    fetchAll("/api/v1/currencies/?is_active=true").then(setCurrencies).catch(() => undefined);
  }, []);

  function openCreate() {
    setEditing(null);
    setHeader({
      invoice_no: "",
      purchase_date: new Date().toISOString().slice(0, 10),
      location: "",
      supplier: "",
      notes: "",
    });
    setLines([emptyLine()]);
    setFormError("");
    setShowForm(true);
  }

  function openEdit(purchase: Purchase) {
    setEditing(purchase);
    setHeader({
      invoice_no: purchase.invoice_no,
      purchase_date: purchase.purchase_date,
      location: String(purchase.location),
      supplier: String(purchase.supplier),
      notes: purchase.notes,
    });
    setLines(
      purchase.lines.map((line) => ({
        id: line.id,
        product: String(line.product),
        quantity: line.quantity,
        unit_price: line.unit_price,
        currency: String(line.currency),
        exchange_rate: line.exchange_rate,
        gst_rate_percent: line.gst_rate_percent,
        collected_qty: "",
        notes: line.notes,
        collected: line.collected,
      })),
    );
    setFormError("");
    setShowForm(true);
  }

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    setSaving(true);
    const payload = {
      ...header,
      location: Number(header.location),
      supplier: Number(header.supplier),
      lines: lines.map((line) => ({
        ...(line.id !== undefined ? { id: line.id } : {}),
        product: Number(line.product),
        quantity: line.quantity,
        unit_price: line.unit_price,
        currency: Number(line.currency),
        ...(line.exchange_rate !== "" ? { exchange_rate: line.exchange_rate } : {}),
        ...(line.gst_rate_percent !== ""
          ? { gst_rate_percent: line.gst_rate_percent }
          : {}),
        ...(!line.id && line.collected_qty !== ""
          ? { collected_qty: line.collected_qty }
          : {}),
        notes: line.notes,
      })),
    };
    try {
      if (editing) {
        await api(`/api/v1/purchases/${editing.id}/`, { method: "PUT", body: payload });
      } else {
        await api("/api/v1/purchases/", { method: "POST", body: payload });
      }
      setShowForm(false);
      await load();
    } catch (err) {
      setFormError(errorMessage(err));
    } finally {
      setSaving(false);
    }
  }

  async function remove(purchase: Purchase) {
    if (
      !window.confirm(
        `Delete purchase ${purchase.invoice_no}? Pending and collected stock will be reversed; the record stays traceable in the ledger and audit history.`,
      )
    )
      return;
    try {
      await api(`/api/v1/purchases/${purchase.id}/`, { method: "DELETE" });
      await load();
    } catch (err) {
      setError(errorMessage(err));
    }
  }

  const inputCls =
    "w-full rounded border border-edge px-2 py-1.5 text-sm focus:border-primary focus:outline-none";

  return (
    <div>
      <div className="mb-4 flex flex-wrap items-center gap-3">
        <h1 className="text-xl font-semibold">Purchases</h1>
        <span className="text-sm text-muted">{count} invoices</span>
        <div className="ml-auto flex items-center gap-2">
          <input
            className="rounded border border-edge px-3 py-1.5 text-sm"
            placeholder="Search invoice, product, supplier…"
            value={search}
            onChange={(e) => { setSearch(e.target.value); setPage(1); }}
          />
          {writable && (
            <button
              className="rounded bg-primary px-3 py-1.5 text-sm font-medium text-on-primary hover:bg-primary-strong"
              onClick={openCreate}
            >
              New Purchase
            </button>
          )}
        </div>
      </div>

      <div className="mb-4 grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-5">
        {[
          ["Total quantity", totals.total_quantity],
          ["Collected", totals.total_collected],
          ["Pending", totals.total_pending],
          ["Value (AED)", totals.total_value_aed],
          ["GST (AED)", totals.total_gst_aed],
        ].map(([label, value]) => (
          <div key={label} className="rounded-lg border border-edge bg-surface px-4 py-3">
            <div className="text-xs uppercase text-muted">{label}</div>
            <div className="text-lg font-semibold">{value ?? "—"}</div>
          </div>
        ))}
      </div>

      {error && <p className="mb-3 text-sm text-danger">{error}</p>}

      <div className="overflow-x-auto rounded-lg border border-edge bg-surface">
        <table className="w-full text-left text-sm">
          <thead className="border-b border-edge bg-surface-2 text-xs uppercase text-muted">
            <tr>
              <th className="px-4 py-2.5 font-medium">Invoice</th>
              <th className="px-4 py-2.5 font-medium">Date</th>
              <th className="px-4 py-2.5 font-medium">Location</th>
              <th className="px-4 py-2.5 font-medium">Supplier</th>
              <th className="px-4 py-2.5 font-medium">Lines</th>
              <th className="px-4 py-2.5 font-medium">Status</th>
              <th className="px-4 py-2.5" />
            </tr>
          </thead>
          <tbody>
            {rows.map((purchase) => (
              <Fragment key={purchase.id}>
                <tr
                  className="cursor-pointer border-b border-edge-2 last:border-0 hover:bg-surface-2"
                  onClick={() =>
                    setExpanded(expanded === purchase.id ? null : purchase.id)
                  }
                >
                  <td className="px-4 py-2 font-medium">{purchase.invoice_no}</td>
                  <td className="px-4 py-2">{purchase.purchase_date}</td>
                  <td className="px-4 py-2">{purchase.location_name}</td>
                  <td className="px-4 py-2">{purchase.supplier_name}</td>
                  <td className="px-4 py-2">{purchase.lines.length}</td>
                  <td className="px-4 py-2">
                    <StatusBadge status={purchase.status} />
                  </td>
                  <td className="px-4 py-2 text-right whitespace-nowrap">
                    {writable && (
                      <>
                        <button
                          className="text-primary hover:underline"
                          onClick={(e) => {
                            e.stopPropagation();
                            openEdit(purchase);
                          }}
                        >
                          Edit
                        </button>
                        <button
                          className="ml-3 text-danger hover:underline"
                          onClick={(e) => {
                            e.stopPropagation();
                            remove(purchase);
                          }}
                        >
                          Delete
                        </button>
                      </>
                    )}
                  </td>
                </tr>
                {expanded === purchase.id && (
                  <tr className="border-b border-edge-2">
                    <td colSpan={7} className="bg-surface-2 px-6 py-3">
                      <table className="w-full text-xs">
                        <thead className="text-muted">
                          <tr>
                            <th className="py-1 pr-3 text-left font-medium">Product</th>
                            <th className="py-1 pr-3 text-right font-medium">Qty</th>
                            <th className="py-1 pr-3 text-right font-medium">Unit price</th>
                            <th className="py-1 pr-3 text-right font-medium">Rate→AED</th>
                            <th className="py-1 pr-3 text-right font-medium">Value AED</th>
                            <th className="py-1 pr-3 text-right font-medium">GST</th>
                            <th className="py-1 pr-3 text-right font-medium">Collected</th>
                            <th className="py-1 pr-3 text-right font-medium">Pending</th>
                            <th className="py-1 text-left font-medium">Status</th>
                          </tr>
                        </thead>
                        <tbody>
                          {purchase.lines.map((line) => (
                            <tr key={line.id} className="border-t border-edge">
                              <td className="py-1.5 pr-3">{line.product_name}</td>
                              <td className="py-1.5 pr-3 text-right">{line.quantity}</td>
                              <td className="py-1.5 pr-3 text-right">
                                {line.unit_price} {line.currency_code}
                              </td>
                              <td className="py-1.5 pr-3 text-right">{line.exchange_rate}</td>
                              <td className="py-1.5 pr-3 text-right">{line.total_value_aed}</td>
                              <td className="py-1.5 pr-3 text-right">
                                {line.gst_amount} {line.currency_code}
                              </td>
                              <td className="py-1.5 pr-3 text-right">{line.collected}</td>
                              <td className="py-1.5 pr-3 text-right">{line.pending}</td>
                              <td className="py-1.5">
                                <StatusBadge status={line.status} />
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                      <AttachmentsPanel
                        module="purchases"
                        recordId={purchase.id}
                        canWrite={writable}
                      />
                    </td>
                  </tr>
                )}
              </Fragment>
            ))}
            {rows.length === 0 && (
              <tr>
                <td className="px-4 py-6 text-center text-faint" colSpan={7}>
                  No purchases
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      <Pagination page={page} count={count} onPage={setPage} />

      {showForm && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
          <form
            onSubmit={submit}
            className="max-h-full w-full max-w-4xl overflow-y-auto rounded-lg bg-surface p-6 shadow-xl"
          >
            <h2 className="mb-4 text-lg font-semibold">
              {editing ? `Edit ${editing.invoice_no}` : "New Purchase Invoice"}
            </h2>

            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
              <label className="block text-sm">
                <span className="mb-1 block font-medium text-ink-2">
                  Invoice/reference <span className="text-danger">*</span>
                </span>
                <input
                  className={inputCls}
                  required
                  value={header.invoice_no}
                  onChange={(e) => setHeader({ ...header, invoice_no: e.target.value })}
                />
              </label>
              <label className="block text-sm">
                <span className="mb-1 block font-medium text-ink-2">
                  Purchase date <span className="text-danger">*</span>
                </span>
                <input
                  className={inputCls}
                  type="date"
                  required
                  value={header.purchase_date}
                  onChange={(e) => setHeader({ ...header, purchase_date: e.target.value })}
                />
              </label>
              <label className="block text-sm">
                <span className="mb-1 block font-medium text-ink-2">
                  Location <span className="text-danger">*</span>
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
                <span className="mb-1 block font-medium text-ink-2">
                  Supplier/party <span className="text-danger">*</span>
                </span>
                <select
                  className={inputCls}
                  required
                  value={header.supplier}
                  onChange={(e) => setHeader({ ...header, supplier: e.target.value })}
                >
                  <option value="">— select —</option>
                  {suppliers.map((supplier) => (
                    <option key={supplier.id} value={supplier.id}>
                      {supplier.name}
                    </option>
                  ))}
                </select>
              </label>
            </div>

            <div className="mt-5">
              <div className="mb-2 flex items-center justify-between">
                <h3 className="text-sm font-semibold text-ink-2">Product lines</h3>
                <button
                  type="button"
                  className="text-sm text-primary hover:underline"
                  onClick={() => setLines([...lines, emptyLine()])}
                >
                  + Add line
                </button>
              </div>
              <div className="space-y-3">
                {lines.map((line, index) => {
                  const locked = Boolean(line.id) && Number(line.collected ?? "0") > 0;
                  return (
                    <div
                      key={line.id ?? `new-${index}`}
                      className="grid gap-2 rounded border border-edge p-3 sm:grid-cols-2 lg:grid-cols-7"
                    >
                      <label className="block text-xs lg:col-span-2">
                        <span className="mb-1 block font-medium text-ink-2">
                          Product *
                        </span>
                        <select
                          className={inputCls}
                          required
                          disabled={locked}
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
                        <span className="mb-1 block font-medium text-ink-2">Qty *</span>
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
                        <span className="mb-1 block font-medium text-ink-2">
                          Unit price *
                        </span>
                        <input
                          className={inputCls}
                          type="number"
                          step="any"
                          min="0"
                          required
                          disabled={locked}
                          value={line.unit_price}
                          onChange={(e) => {
                            const next = [...lines];
                            next[index] = { ...line, unit_price: e.target.value };
                            setLines(next);
                          }}
                        />
                      </label>
                      <label className="block text-xs">
                        <span className="mb-1 block font-medium text-ink-2">
                          Currency *
                        </span>
                        <select
                          className={inputCls}
                          required
                          disabled={locked}
                          value={line.currency}
                          onChange={(e) => {
                            const next = [...lines];
                            next[index] = { ...line, currency: e.target.value };
                            setLines(next);
                          }}
                        >
                          <option value="">— select —</option>
                          {currencies.map((currency) => (
                            <option key={currency.id} value={currency.id}>
                              {currency.code}
                            </option>
                          ))}
                        </select>
                      </label>
                      <label className="block text-xs">
                        <span className="mb-1 block font-medium text-ink-2">
                          Rate→AED
                        </span>
                        <input
                          className={inputCls}
                          type="number"
                          step="any"
                          min="0"
                          placeholder="auto"
                          disabled={locked}
                          value={line.exchange_rate}
                          onChange={(e) => {
                            const next = [...lines];
                            next[index] = { ...line, exchange_rate: e.target.value };
                            setLines(next);
                          }}
                        />
                      </label>
                      <label className="block text-xs">
                        <span className="mb-1 block font-medium text-ink-2">
                          {line.id ? "GST %" : "Collected now"}
                        </span>
                        {line.id ? (
                          <input
                            className={inputCls}
                            type="number"
                            step="any"
                            min="0"
                            disabled={locked}
                            value={line.gst_rate_percent}
                            onChange={(e) => {
                              const next = [...lines];
                              next[index] = { ...line, gst_rate_percent: e.target.value };
                              setLines(next);
                            }}
                          />
                        ) : (
                          <input
                            className={inputCls}
                            type="number"
                            step="any"
                            min="0"
                            placeholder="0"
                            value={line.collected_qty}
                            onChange={(e) => {
                              const next = [...lines];
                              next[index] = { ...line, collected_qty: e.target.value };
                              setLines(next);
                            }}
                          />
                        )}
                      </label>
                      <div className="flex items-end justify-end pb-1">
                        {lines.length > 1 && !locked && (
                          <button
                            type="button"
                            className="text-xs text-danger hover:underline"
                            onClick={() => setLines(lines.filter((_, i) => i !== index))}
                          >
                            Remove
                          </button>
                        )}
                        {locked && (
                          <span className="text-xs text-faint">
                            collected: {line.collected}
                          </span>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>

            <label className="mt-4 block text-sm">
              <span className="mb-1 block font-medium text-ink-2">Notes</span>
              <textarea
                className={inputCls}
                rows={2}
                value={header.notes}
                onChange={(e) => setHeader({ ...header, notes: e.target.value })}
              />
            </label>

            {formError && <p className="mt-3 text-sm text-danger">{formError}</p>}
            <div className="mt-5 flex justify-end gap-2">
              <button
                type="button"
                className="rounded border border-edge px-4 py-1.5 text-sm"
                onClick={() => setShowForm(false)}
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={saving}
                className="rounded bg-primary px-4 py-1.5 text-sm font-medium text-on-primary hover:bg-primary-strong disabled:opacity-50"
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
