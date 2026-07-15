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
  notes: string;
}

interface ShipmentLine {
  id: number;
  product: number;
  product_name: string;
  quantity: string;
  received: string;
  remaining: string;
  over_received: boolean;
  status: string;
  notes: string;
}

interface Shipment {
  id: number;
  shipment_no: string;
  shipment_date: string;
  from_location: number;
  from_location_name: string;
  to_location: number;
  to_location_name: string;
  shipment_type: string;
  shipping_cost: string;
  status: string;
  notes: string;
  cancel_reason: string;
  lines: ShipmentLine[];
  created_by_username: string | null;
}

interface ReceiptLine {
  shipment_line: number;
  product_name: string;
  quantity: string;
}

interface Receipt {
  id: number;
  receipt_date: string;
  notes: string;
  lines: ReceiptLine[];
  created_by_username: string | null;
}

interface ListResponse {
  count: number;
  results: Shipment[];
  totals?: Record<string, string>;
}

const emptyLine = (): LineForm => ({ product: "", quantity: "", notes: "" });

const STATUS_STYLES: Record<string, string> = {
  DRAFT: "bg-slate-100 text-slate-600",
  SHIPPED: "bg-amber-50 text-amber-700",
  PARTIALLY_RECEIVED: "bg-blue-50 text-blue-700",
  FULLY_RECEIVED: "bg-green-50 text-green-700",
  CANCELLED: "bg-slate-100 text-slate-500",
};

function StatusBadge({ status }: { status: string }) {
  return (
    <span
      className={`inline-block rounded px-2 py-0.5 text-xs font-medium ${
        STATUS_STYLES[status] ?? "bg-slate-100 text-slate-600"
      }`}
    >
      {status.replaceAll("_", " ")}
    </span>
  );
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

export default function ShipmentsPage() {
  const user = useAuth();
  const writable = canWrite(user?.role, "shipments");

  const [rows, setRows] = useState<Shipment[]>([]);
  const [count, setCount] = useState(0);
  const [totals, setTotals] = useState<Record<string, string>>({});
  const [search, setSearch] = useState("");
  const [expanded, setExpanded] = useState<number | null>(null);
  const [receipts, setReceipts] = useState<Record<number, Receipt[]>>({});
  const [error, setError] = useState("");

  const [showForm, setShowForm] = useState(false);
  const [editing, setEditing] = useState<Shipment | null>(null);
  const [header, setHeader] = useState({
    shipment_date: "",
    from_location: "",
    to_location: "",
    shipment_type: "STANDARD",
    shipping_cost: "",
    notes: "",
  });
  const [lines, setLines] = useState<LineForm[]>([emptyLine()]);
  const [formError, setFormError] = useState("");
  const [saving, setSaving] = useState(false);

  // Receive dialog state: per-line quantities for the selected shipment.
  const [receiving, setReceiving] = useState<Shipment | null>(null);
  const [receiveQty, setReceiveQty] = useState<Record<number, string>>({});
  const [receiveDate, setReceiveDate] = useState("");
  const [receiveError, setReceiveError] = useState("");

  const [products, setProducts] = useState<Option[]>([]);
  const [locations, setLocations] = useState<Option[]>([]);

  const load = useCallback(async () => {
    const query = search ? `?search=${encodeURIComponent(search)}` : "";
    const data = await api<ListResponse>(`/api/v1/shipments/${query}`);
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
    fetchAll("/api/v1/locations/?is_active=true").then(setLocations).catch(() => undefined);
  }, []);

  async function toggleExpand(shipment: Shipment) {
    const next = expanded === shipment.id ? null : shipment.id;
    setExpanded(next);
    if (next !== null && !(next in receipts)) {
      try {
        const data = await api<Receipt[]>(`/api/v1/shipments/${shipment.id}/receipts/`);
        setReceipts((prev) => ({ ...prev, [shipment.id]: data }));
      } catch {
        // Receipts stay collapsed on failure; row data is still shown.
      }
    }
  }

  async function refresh(shipmentId?: number) {
    await load();
    if (shipmentId !== undefined) {
      const data = await api<Receipt[]>(`/api/v1/shipments/${shipmentId}/receipts/`);
      setReceipts((prev) => ({ ...prev, [shipmentId]: data }));
    }
  }

  function openCreate() {
    setEditing(null);
    setHeader({
      shipment_date: new Date().toISOString().slice(0, 10),
      from_location: "",
      to_location: "",
      shipment_type: "STANDARD",
      shipping_cost: "",
      notes: "",
    });
    setLines([emptyLine()]);
    setFormError("");
    setShowForm(true);
  }

  function openEdit(shipment: Shipment) {
    setEditing(shipment);
    setHeader({
      shipment_date: shipment.shipment_date,
      from_location: String(shipment.from_location),
      to_location: String(shipment.to_location),
      shipment_type: shipment.shipment_type,
      shipping_cost: shipment.shipping_cost,
      notes: shipment.notes,
    });
    setLines(
      shipment.lines.map((line) => ({
        id: line.id,
        product: String(line.product),
        quantity: line.quantity,
        notes: line.notes,
      })),
    );
    setFormError("");
    setShowForm(true);
  }

  function formPayload(ship: boolean) {
    return {
      ...header,
      from_location: Number(header.from_location),
      to_location: Number(header.to_location),
      shipping_cost: header.shipping_cost === "" ? "0.00" : header.shipping_cost,
      ship,
      lines: lines.map((line) => ({
        ...(line.id !== undefined ? { id: line.id } : {}),
        product: Number(line.product),
        quantity: line.quantity,
        notes: line.notes,
      })),
    };
  }

  async function submit(ship: boolean) {
    setSaving(true);
    setFormError("");
    try {
      if (editing) {
        await api(`/api/v1/shipments/${editing.id}/`, {
          method: "PUT",
          body: formPayload(false),
        });
        if (ship) await shipNow(editing, false);
      } else {
        await withNegativeConfirm(
          "/api/v1/shipments/",
          { method: "POST", body: formPayload(ship) },
          "This shipment takes source stock negative. Ship anyway?",
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

  async function shipNow(shipment: Shipment, reload = true) {
    await withNegativeConfirm(
      `/api/v1/shipments/${shipment.id}/ship/`,
      { method: "POST" },
      "This shipment takes source stock negative. Ship anyway?",
    );
    if (reload) await load();
  }

  function openReceive(shipment: Shipment) {
    setReceiving(shipment);
    setReceiveDate(new Date().toISOString().slice(0, 10));
    setReceiveQty({});
    setReceiveError("");
  }

  async function submitReceive() {
    if (!receiving) return;
    const receiptLines = Object.entries(receiveQty)
      .filter(([, qty]) => qty !== "" && Number(qty) > 0)
      .map(([lineId, qty]) => ({ shipment_line: Number(lineId), quantity: qty }));
    if (receiptLines.length === 0) {
      setReceiveError("Enter a received quantity on at least one line.");
      return;
    }
    const overReceived = receiving.lines.filter((line) => {
      const qty = receiveQty[line.id];
      return qty !== undefined && qty !== "" && Number(qty) > Number(line.remaining);
    });
    if (
      overReceived.length > 0 &&
      !window.confirm(
        `Received quantity exceeds the remaining shipped quantity for: ${overReceived
          .map((line) => line.product_name)
          .join(", ")}. Over-receiving is allowed but will be flagged. Continue?`,
      )
    )
      return;
    setReceiveError("");
    try {
      await api(`/api/v1/shipments/${receiving.id}/receipts/`, {
        method: "POST",
        body: { receipt_date: receiveDate, notes: "", lines: receiptLines },
      });
      const id = receiving.id;
      setReceiving(null);
      await refresh(id);
    } catch (err) {
      setReceiveError(errorMessage(err));
    }
  }

  async function cancelShipment(shipment: Shipment) {
    const reason = window.prompt(
      `Cancel shipment ${shipment.shipment_no}? Unreceived stock returns to ${shipment.from_location_name}. Reason:`,
    );
    if (reason === null) return;
    try {
      await api(`/api/v1/shipments/${shipment.id}/cancel/`, {
        method: "POST",
        body: { reason },
      });
      await load();
    } catch (err) {
      setError(errorMessage(err));
    }
  }

  async function remove(shipment: Shipment) {
    if (
      !window.confirm(
        `Delete shipment ${shipment.shipment_no}? All of its stock movements will be reversed; the record stays traceable in the ledger and audit history.`,
      )
    )
      return;
    try {
      await withNegativeConfirm(
        `/api/v1/shipments/${shipment.id}/`,
        { method: "DELETE" },
        "Reversing this shipment takes destination stock negative. Continue?",
      );
      await load();
    } catch (err) {
      setError(errorMessage(err));
    }
  }

  async function undoReceipt(shipment: Shipment, receipt: Receipt) {
    if (
      !window.confirm(
        `Undo receipt of ${receipt.receipt_date}? Received stock returns to in-transit.`,
      )
    )
      return;
    try {
      await withNegativeConfirm(
        `/api/v1/shipments/${shipment.id}/receipts/${receipt.id}/`,
        { method: "DELETE" },
        "Undoing this receipt takes destination stock negative. Continue?",
      );
      await refresh(shipment.id);
    } catch (err) {
      setError(errorMessage(err));
    }
  }

  const inputCls =
    "w-full rounded border border-slate-300 px-2 py-1.5 text-sm focus:border-blue-500 focus:outline-none";

  return (
    <div>
      <div className="mb-4 flex flex-wrap items-center gap-3">
        <h1 className="text-xl font-semibold">Shipments</h1>
        <span className="text-sm text-slate-500">{count} shipments</span>
        <div className="ml-auto flex items-center gap-2">
          <input
            className="rounded border border-slate-300 px-3 py-1.5 text-sm"
            placeholder="Search shipment #, product…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
          {writable && (
            <button
              className="rounded bg-blue-700 px-3 py-1.5 text-sm font-medium text-white hover:bg-blue-800"
              onClick={openCreate}
            >
              New Shipment
            </button>
          )}
        </div>
      </div>

      <div className="mb-4 grid grid-cols-2 gap-3 sm:grid-cols-3">
        {[
          ["Total shipped", totals.total_shipped],
          ["Received", totals.total_received],
          ["In transit / remaining", totals.total_remaining],
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
              <th className="px-4 py-2.5 font-medium">Shipment #</th>
              <th className="px-4 py-2.5 font-medium">Date</th>
              <th className="px-4 py-2.5 font-medium">From → To</th>
              <th className="px-4 py-2.5 font-medium">Type</th>
              <th className="px-4 py-2.5 font-medium">Lines</th>
              <th className="px-4 py-2.5 font-medium">Status</th>
              <th className="px-4 py-2.5" />
            </tr>
          </thead>
          <tbody>
            {rows.map((shipment) => (
              <Fragment key={shipment.id}>
                <tr
                  className="cursor-pointer border-b border-slate-100 last:border-0 hover:bg-slate-50"
                  onClick={() => toggleExpand(shipment)}
                >
                  <td className="px-4 py-2 font-medium">
                    {shipment.shipment_no}
                    {shipment.lines.some((line) => line.over_received) && (
                      <span
                        className="ml-2 inline-block rounded bg-orange-100 px-1.5 py-0.5 text-xs font-medium text-orange-700"
                        title="One or more lines received more than was shipped"
                      >
                        over-received
                      </span>
                    )}
                  </td>
                  <td className="px-4 py-2">{shipment.shipment_date}</td>
                  <td className="px-4 py-2">
                    {shipment.from_location_name} → {shipment.to_location_name}
                  </td>
                  <td className="px-4 py-2">
                    {shipment.shipment_type === "DUBAI_KARACHI"
                      ? "Dubai → Karachi transfer"
                      : "Standard"}
                  </td>
                  <td className="px-4 py-2">{shipment.lines.length}</td>
                  <td className="px-4 py-2">
                    <StatusBadge status={shipment.status} />
                  </td>
                  <td className="px-4 py-2 text-right whitespace-nowrap">
                    {writable && (
                      <>
                        {shipment.status === "DRAFT" && (
                          <>
                            <button
                              className="text-blue-700 hover:underline"
                              onClick={(e) => {
                                e.stopPropagation();
                                shipNow(shipment).catch((err) => setError(errorMessage(err)));
                              }}
                            >
                              Ship
                            </button>
                            <button
                              className="ml-3 text-blue-700 hover:underline"
                              onClick={(e) => {
                                e.stopPropagation();
                                openEdit(shipment);
                              }}
                            >
                              Edit
                            </button>
                          </>
                        )}
                        {(shipment.status === "SHIPPED" ||
                          shipment.status === "PARTIALLY_RECEIVED" ||
                          shipment.status === "FULLY_RECEIVED") && (
                          <button
                            className="text-blue-700 hover:underline"
                            onClick={(e) => {
                              e.stopPropagation();
                              openReceive(shipment);
                            }}
                          >
                            Receive
                          </button>
                        )}
                        {(shipment.status === "SHIPPED" ||
                          shipment.status === "PARTIALLY_RECEIVED" ||
                          shipment.status === "DRAFT") && (
                          <button
                            className="ml-3 text-slate-600 hover:underline"
                            onClick={(e) => {
                              e.stopPropagation();
                              cancelShipment(shipment);
                            }}
                          >
                            Cancel
                          </button>
                        )}
                        <button
                          className="ml-3 text-red-600 hover:underline"
                          onClick={(e) => {
                            e.stopPropagation();
                            remove(shipment);
                          }}
                        >
                          Delete
                        </button>
                      </>
                    )}
                  </td>
                </tr>
                {expanded === shipment.id && (
                  <tr className="border-b border-slate-100">
                    <td colSpan={7} className="bg-slate-50 px-6 py-3">
                      <table className="w-full text-xs">
                        <thead className="text-slate-500">
                          <tr>
                            <th className="py-1 pr-3 text-left font-medium">Product</th>
                            <th className="py-1 pr-3 text-right font-medium">Shipped</th>
                            <th className="py-1 pr-3 text-right font-medium">Received</th>
                            <th className="py-1 pr-3 text-right font-medium">Remaining</th>
                            <th className="py-1 text-left font-medium">Status</th>
                          </tr>
                        </thead>
                        <tbody>
                          {shipment.lines.map((line) => (
                            <tr
                              key={line.id}
                              className={`border-t border-slate-200 ${
                                line.over_received ? "bg-orange-50" : ""
                              }`}
                            >
                              <td className="py-1.5 pr-3">
                                {line.product_name}
                                {line.over_received && (
                                  <span className="ml-2 font-medium text-orange-700">
                                    over-received
                                  </span>
                                )}
                              </td>
                              <td className="py-1.5 pr-3 text-right">{line.quantity}</td>
                              <td className="py-1.5 pr-3 text-right">{line.received}</td>
                              <td
                                className={`py-1.5 pr-3 text-right ${
                                  Number(line.remaining) < 0
                                    ? "font-medium text-orange-700"
                                    : ""
                                }`}
                              >
                                {line.remaining}
                              </td>
                              <td className="py-1.5">
                                <StatusBadge status={line.status} />
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>

                      {shipment.cancel_reason && (
                        <p className="mt-2 text-xs text-slate-500">
                          Cancelled: {shipment.cancel_reason}
                        </p>
                      )}

                      <h3 className="mt-3 mb-1 text-xs font-semibold text-slate-600">
                        Receipts
                      </h3>
                      {(receipts[shipment.id] ?? []).length === 0 ? (
                        <p className="text-xs text-slate-400">Nothing received yet</p>
                      ) : (
                        <table className="w-full text-xs">
                          <tbody>
                            {(receipts[shipment.id] ?? []).map((receipt) => (
                              <tr key={receipt.id} className="border-t border-slate-200">
                                <td className="py-1.5 pr-3">{receipt.receipt_date}</td>
                                <td className="py-1.5 pr-3">
                                  {receipt.lines.map((line) => (
                                    <span key={line.shipment_line} className="mr-3">
                                      {line.quantity} × {line.product_name}
                                    </span>
                                  ))}
                                </td>
                                <td className="py-1.5 pr-3">
                                  {receipt.created_by_username ?? "—"}
                                </td>
                                {writable && (
                                  <td className="py-1.5 text-right">
                                    <button
                                      className="text-red-600 hover:underline"
                                      onClick={() => undoReceipt(shipment, receipt)}
                                    >
                                      Undo
                                    </button>
                                  </td>
                                )}
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      )}
                    </td>
                  </tr>
                )}
              </Fragment>
            ))}
            {rows.length === 0 && (
              <tr>
                <td className="px-4 py-6 text-center text-slate-400" colSpan={7}>
                  No shipments
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      {showForm && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
          <form
            onSubmit={(e) => {
              e.preventDefault();
              submit(false);
            }}
            className="max-h-full w-full max-w-3xl overflow-y-auto rounded-lg bg-white p-6 shadow-xl"
          >
            <h2 className="mb-4 text-lg font-semibold">
              {editing ? `Edit ${editing.shipment_no}` : "New Shipment"}
            </h2>

            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
              <label className="block text-sm">
                <span className="mb-1 block font-medium text-slate-700">
                  Shipment date <span className="text-red-500">*</span>
                </span>
                <input
                  className={inputCls}
                  type="date"
                  required
                  value={header.shipment_date}
                  onChange={(e) => setHeader({ ...header, shipment_date: e.target.value })}
                />
              </label>
              <label className="block text-sm">
                <span className="mb-1 block font-medium text-slate-700">
                  From location <span className="text-red-500">*</span>
                </span>
                <select
                  className={inputCls}
                  required
                  value={header.from_location}
                  onChange={(e) => setHeader({ ...header, from_location: e.target.value })}
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
                  To location <span className="text-red-500">*</span>
                </span>
                <select
                  className={inputCls}
                  required
                  value={header.to_location}
                  onChange={(e) => setHeader({ ...header, to_location: e.target.value })}
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
                <span className="mb-1 block font-medium text-slate-700">Type</span>
                <select
                  className={inputCls}
                  value={header.shipment_type}
                  onChange={(e) => setHeader({ ...header, shipment_type: e.target.value })}
                >
                  <option value="STANDARD">Standard</option>
                  <option value="DUBAI_KARACHI">Dubai → Karachi transfer</option>
                </select>
              </label>
              <label className="block text-sm">
                <span className="mb-1 block font-medium text-slate-700">
                  Shipping cost (excluded from stock value)
                </span>
                <input
                  className={inputCls}
                  type="number"
                  step="any"
                  min="0"
                  placeholder="0.00"
                  value={header.shipping_cost}
                  onChange={(e) => setHeader({ ...header, shipping_cost: e.target.value })}
                />
              </label>
            </div>

            <div className="mt-5">
              <div className="mb-2 flex items-center justify-between">
                <h3 className="text-sm font-semibold text-slate-700">Product lines</h3>
                {(!editing || editing.status === "DRAFT") && (
                  <button
                    type="button"
                    className="text-sm text-blue-700 hover:underline"
                    onClick={() => setLines([...lines, emptyLine()])}
                  >
                    + Add line
                  </button>
                )}
              </div>
              <div className="space-y-3">
                {lines.map((line, index) => (
                  <div
                    key={line.id ?? `new-${index}`}
                    className="grid gap-2 rounded border border-slate-200 p-3 sm:grid-cols-2 lg:grid-cols-4"
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
                className="rounded border border-blue-700 px-4 py-1.5 text-sm font-medium text-blue-700 hover:bg-blue-50 disabled:opacity-50"
              >
                {saving ? "Saving…" : "Save Draft"}
              </button>
              {(!editing || editing.status === "DRAFT") && (
                <button
                  type="button"
                  disabled={saving}
                  className="rounded bg-blue-700 px-4 py-1.5 text-sm font-medium text-white hover:bg-blue-800 disabled:opacity-50"
                  onClick={() => submit(true)}
                >
                  {saving ? "Saving…" : "Save & Ship"}
                </button>
              )}
            </div>
          </form>
        </div>
      )}

      {receiving && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
          <div className="max-h-full w-full max-w-2xl overflow-y-auto rounded-lg bg-white p-6 shadow-xl">
            <h2 className="mb-1 text-lg font-semibold">
              Receive {receiving.shipment_no}
            </h2>
            <p className="mb-4 text-sm text-slate-500">
              {receiving.from_location_name} → {receiving.to_location_name}. Partial
              receiving is allowed; receiving more than remaining is flagged as
              over-received.
            </p>

            <table className="mb-4 w-full text-left text-sm">
              <thead className="border-b border-slate-200 text-xs uppercase text-slate-500">
                <tr>
                  <th className="py-2 pr-3 font-medium">Product</th>
                  <th className="py-2 pr-3 text-right font-medium">Shipped</th>
                  <th className="py-2 pr-3 text-right font-medium">Received</th>
                  <th className="py-2 pr-3 text-right font-medium">Remaining</th>
                  <th className="py-2 text-right font-medium">Receive now</th>
                </tr>
              </thead>
              <tbody>
                {receiving.lines.map((line) => (
                  <tr key={line.id} className="border-b border-slate-100 last:border-0">
                    <td className="py-2 pr-3">{line.product_name}</td>
                    <td className="py-2 pr-3 text-right">{line.quantity}</td>
                    <td className="py-2 pr-3 text-right">{line.received}</td>
                    <td className="py-2 pr-3 text-right">{line.remaining}</td>
                    <td className="py-2 text-right">
                      <input
                        type="number"
                        step="any"
                        min="0"
                        className="w-24 rounded border border-slate-300 px-2 py-1 text-right text-sm focus:border-blue-500 focus:outline-none"
                        value={receiveQty[line.id] ?? ""}
                        onChange={(e) =>
                          setReceiveQty((prev) => ({ ...prev, [line.id]: e.target.value }))
                        }
                      />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>

            <label className="mb-4 block text-sm">
              <span className="mb-1 block font-medium text-slate-700">Receipt date</span>
              <input
                type="date"
                className="rounded border border-slate-300 px-2 py-1.5 text-sm focus:border-blue-500 focus:outline-none"
                value={receiveDate}
                onChange={(e) => setReceiveDate(e.target.value)}
              />
            </label>

            {receiveError && <p className="mb-3 text-sm text-red-600">{receiveError}</p>}
            <div className="flex justify-end gap-2">
              <button
                className="rounded border border-slate-300 px-4 py-1.5 text-sm"
                onClick={() => setReceiving(null)}
              >
                Cancel
              </button>
              <button
                className="rounded bg-blue-700 px-4 py-1.5 text-sm font-medium text-white hover:bg-blue-800"
                onClick={submitReceive}
              >
                Record Receipt
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
