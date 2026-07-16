"use client";

import { useCallback, useEffect, useState } from "react";

import { api, ApiError, errorMessage } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { canWrite } from "@/lib/permissions";

interface PurchaseLine {
  id: number;
  product_name: string;
  quantity: string;
  collected: string;
  pending: string;
  refunded: string;
  net: string;
  status: string;
  unit_price: string;
  currency_code: string;
}

interface Purchase {
  id: number;
  invoice_no: string;
  purchase_date: string;
  location_name: string;
  supplier_name: string;
  status: string;
  lines: PurchaseLine[];
}

interface RefundLine {
  purchase_line: number;
  product_name: string;
  source: "PENDING" | "RECEIVED";
  quantity: string;
  value_reversal: string;
  value_reversal_aed: string;
  gst_reversal: string;
  gst_reversal_aed: string;
}

interface Refund {
  id: number;
  refund_no: string;
  refund_date: string;
  reason: string;
  notes: string;
  lines: RefundLine[];
  created_by_username: string | null;
}

export default function PurchaseRefundsPage() {
  const user = useAuth();
  const writable = canWrite(user?.role, "purchases");

  const [search, setSearch] = useState("");
  const [matches, setMatches] = useState<Purchase[]>([]);
  const [purchase, setPurchase] = useState<Purchase | null>(null);
  const [refunds, setRefunds] = useState<Refund[]>([]);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  // Per-line inputs on the selected invoice.
  const [inputs, setInputs] = useState<
    Record<number, { quantity: string; source: "PENDING" | "RECEIVED" }>
  >({});
  const [reason, setReason] = useState("");
  const [refundDate, setRefundDate] = useState(new Date().toISOString().slice(0, 10));
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (!search) {
      setMatches([]);
      return;
    }
    const handle = setTimeout(() => {
      api<{ results: Purchase[] }>(
        `/api/v1/purchases/?search=${encodeURIComponent(search)}`,
      )
        .then((data) => setMatches(data.results))
        .catch(() => undefined);
    }, 250);
    return () => clearTimeout(handle);
  }, [search]);

  const loadPurchase = useCallback(async (id: number) => {
    const [detail, refundList] = await Promise.all([
      api<Purchase>(`/api/v1/purchases/${id}/`),
      api<Refund[]>(`/api/v1/purchases/${id}/refunds/`),
    ]);
    setPurchase(detail);
    setRefunds(refundList);
    setInputs({});
  }, []);

  function select(candidate: Purchase) {
    setSearch("");
    setMatches([]);
    setError("");
    setNotice("");
    loadPurchase(candidate.id).catch((err) => setError(errorMessage(err)));
  }

  async function submitRefund() {
    if (!purchase) return;
    const lines = Object.entries(inputs)
      .filter(([, value]) => value.quantity !== "" && Number(value.quantity) > 0)
      .map(([lineId, value]) => ({
        purchase_line: Number(lineId),
        source: value.source,
        quantity: value.quantity,
      }));
    if (lines.length === 0) {
      setError("Enter a refund/cancellation quantity on at least one line.");
      return;
    }
    setSaving(true);
    setError("");
    setNotice("");
    const body = { refund_date: refundDate, reason, notes: "", lines };
    try {
      try {
        await api(`/api/v1/purchases/${purchase.id}/refunds/`, { method: "POST", body });
      } catch (err) {
        if (
          err instanceof ApiError &&
          typeof err.body === "object" &&
          err.body !== null &&
          (err.body as { code?: string[] | string }).code?.toString().includes(
            "negative_stock_confirmation_required",
          ) &&
          window.confirm("This refund makes physical stock negative. Continue anyway?")
        ) {
          await api(`/api/v1/purchases/${purchase.id}/refunds/?confirm_negative=true`, {
            method: "POST",
            body,
          });
        } else {
          throw err;
        }
      }
      setNotice("Refund/cancellation recorded. Original purchase history is preserved.");
      setReason("");
      await loadPurchase(purchase.id);
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setSaving(false);
    }
  }

  async function removeRefund(refund: Refund) {
    if (!purchase) return;
    if (!window.confirm(`Undo refund ${refund.refund_no}? Its stock reversal will be reversed.`))
      return;
    try {
      await api(`/api/v1/purchases/${purchase.id}/refunds/${refund.id}/`, {
        method: "DELETE",
      });
      await loadPurchase(purchase.id);
    } catch (err) {
      setError(errorMessage(err));
    }
  }

  const inputCls =
    "rounded border border-edge px-2 py-1 text-sm focus:border-primary focus:outline-none";

  return (
    <div>
      <div className="mb-4 flex flex-wrap items-center gap-3">
        <h1 className="text-xl font-semibold">Purchase Refunds / Cancellations</h1>
        <div className="relative ml-auto">
          <input
            className="w-72 rounded border border-edge px-3 py-1.5 text-sm"
            placeholder="Find purchase invoice…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
          {matches.length > 0 && (
            <div className="absolute right-0 z-10 mt-1 w-96 rounded-lg border border-edge bg-surface shadow-lg">
              {matches.map((candidate) => (
                <button
                  key={candidate.id}
                  className="block w-full px-3 py-2 text-left text-sm hover:bg-surface-2"
                  onClick={() => select(candidate)}
                >
                  <span className="font-medium">{candidate.invoice_no}</span>
                  <span className="text-muted">
                    {" "}
                    · {candidate.purchase_date} · {candidate.location_name} ·{" "}
                    {candidate.supplier_name}
                  </span>
                </button>
              ))}
            </div>
          )}
        </div>
      </div>

      {error && <p className="mb-3 text-sm text-danger">{error}</p>}
      {notice && <p className="mb-3 text-sm text-success">{notice}</p>}

      {!purchase && (
        <p className="rounded-lg border border-dashed border-edge bg-surface px-4 py-10 text-center text-sm text-muted">
          Search for a purchase invoice above to load its product lines, then refund or
          cancel quantities line by line.
        </p>
      )}

      {purchase && (
        <>
          <div className="mb-4 rounded-lg border border-edge bg-surface px-4 py-3 text-sm">
            <span className="font-semibold">{purchase.invoice_no}</span>
            <span className="text-muted">
              {" "}
              · {purchase.purchase_date} · {purchase.location_name} ·{" "}
              {purchase.supplier_name} · {purchase.status.replaceAll("_", " ")}
            </span>
          </div>

          <div className="mb-4 overflow-x-auto rounded-lg border border-edge bg-surface">
            <table className="w-full text-left text-sm">
              <thead className="border-b border-edge bg-surface-2 text-xs uppercase text-muted">
                <tr>
                  <th className="px-4 py-2.5 font-medium">Product</th>
                  <th className="px-4 py-2.5 text-right font-medium">Qty</th>
                  <th className="px-4 py-2.5 text-right font-medium">Collected</th>
                  <th className="px-4 py-2.5 text-right font-medium">Pending</th>
                  <th className="px-4 py-2.5 text-right font-medium">Refunded</th>
                  <th className="px-4 py-2.5 text-right font-medium">Net</th>
                  {writable && (
                    <>
                      <th className="px-4 py-2.5 text-right font-medium">Refund qty</th>
                      <th className="px-4 py-2.5 font-medium">From</th>
                    </>
                  )}
                </tr>
              </thead>
              <tbody>
                {purchase.lines.map((line) => (
                  <tr key={line.id} className="border-b border-edge-2 last:border-0">
                    <td className="px-4 py-2">{line.product_name}</td>
                    <td className="px-4 py-2 text-right">{line.quantity}</td>
                    <td className="px-4 py-2 text-right">{line.collected}</td>
                    <td className="px-4 py-2 text-right">{line.pending}</td>
                    <td className="px-4 py-2 text-right">{line.refunded}</td>
                    <td className="px-4 py-2 text-right font-medium">{line.net}</td>
                    {writable && (
                      <>
                        <td className="px-4 py-2 text-right">
                          <input
                            type="number"
                            step="any"
                            min="0"
                            className={`${inputCls} w-24 text-right`}
                            value={inputs[line.id]?.quantity ?? ""}
                            onChange={(e) =>
                              setInputs((prev) => ({
                                ...prev,
                                [line.id]: {
                                  source: prev[line.id]?.source ?? "PENDING",
                                  quantity: e.target.value,
                                },
                              }))
                            }
                          />
                        </td>
                        <td className="px-4 py-2">
                          <select
                            className={inputCls}
                            value={inputs[line.id]?.source ?? "PENDING"}
                            onChange={(e) =>
                              setInputs((prev) => ({
                                ...prev,
                                [line.id]: {
                                  quantity: prev[line.id]?.quantity ?? "",
                                  source: e.target.value as "PENDING" | "RECEIVED",
                                },
                              }))
                            }
                          >
                            <option value="PENDING">Pending (cancel)</option>
                            <option value="RECEIVED">Received (return stock)</option>
                          </select>
                        </td>
                      </>
                    )}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {writable && (
            <div className="mb-6 flex flex-wrap items-end gap-3 rounded-lg border border-edge bg-surface px-4 py-3 text-sm">
              <label className="block">
                <span className="mb-1 block font-medium text-ink-2">Refund date</span>
                <input
                  type="date"
                  className={inputCls}
                  value={refundDate}
                  onChange={(e) => setRefundDate(e.target.value)}
                />
              </label>
              <label className="block grow">
                <span className="mb-1 block font-medium text-ink-2">
                  Reason <span className="text-danger">*</span>
                </span>
                <input
                  className={`${inputCls} w-full`}
                  placeholder="e.g. supplier cancelled remaining units"
                  value={reason}
                  onChange={(e) => setReason(e.target.value)}
                />
              </label>
              <button
                className="rounded bg-primary px-4 py-1.5 text-sm font-medium text-on-primary hover:bg-primary-strong disabled:opacity-50"
                disabled={saving || !reason.trim()}
                onClick={submitRefund}
              >
                {saving ? "Saving…" : "Record Refund/Cancellation"}
              </button>
            </div>
          )}

          <h2 className="mb-2 text-sm font-semibold text-ink-2">
            Refund history for this invoice
          </h2>
          <div className="overflow-x-auto rounded-lg border border-edge bg-surface">
            <table className="w-full text-left text-sm">
              <thead className="border-b border-edge bg-surface-2 text-xs uppercase text-muted">
                <tr>
                  <th className="px-4 py-2.5 font-medium">Refund #</th>
                  <th className="px-4 py-2.5 font-medium">Date</th>
                  <th className="px-4 py-2.5 font-medium">Lines</th>
                  <th className="px-4 py-2.5 text-right font-medium">Value reversed (AED)</th>
                  <th className="px-4 py-2.5 text-right font-medium">GST reversed (AED)</th>
                  <th className="px-4 py-2.5 font-medium">Reason</th>
                  <th className="px-4 py-2.5 font-medium">By</th>
                  {writable && <th className="px-4 py-2.5" />}
                </tr>
              </thead>
              <tbody>
                {refunds.map((refund) => {
                  const totalValue = refund.lines.reduce(
                    (sum, line) => sum + Number(line.value_reversal_aed),
                    0,
                  );
                  const totalGst = refund.lines.reduce(
                    (sum, line) => sum + Number(line.gst_reversal_aed),
                    0,
                  );
                  return (
                    <tr key={refund.id} className="border-b border-edge-2 last:border-0">
                      <td className="px-4 py-2 font-medium">{refund.refund_no}</td>
                      <td className="px-4 py-2">{refund.refund_date}</td>
                      <td className="px-4 py-2 text-xs">
                        {refund.lines.map((line) => (
                          <div key={`${refund.id}-${line.purchase_line}`}>
                            {line.quantity} × {line.product_name}{" "}
                            <span className="text-muted">
                              ({line.source === "PENDING" ? "cancelled" : "returned"})
                            </span>
                          </div>
                        ))}
                      </td>
                      <td className="px-4 py-2 text-right">{totalValue.toFixed(2)}</td>
                      <td className="px-4 py-2 text-right">{totalGst.toFixed(2)}</td>
                      <td className="px-4 py-2">{refund.reason}</td>
                      <td className="px-4 py-2">{refund.created_by_username ?? "—"}</td>
                      {writable && (
                        <td className="px-4 py-2 text-right">
                          <button
                            className="text-danger hover:underline"
                            onClick={() => removeRefund(refund)}
                          >
                            Undo
                          </button>
                        </td>
                      )}
                    </tr>
                  );
                })}
                {refunds.length === 0 && (
                  <tr>
                    <td className="px-4 py-6 text-center text-faint" colSpan={8}>
                      No refunds/cancellations recorded for this invoice
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
