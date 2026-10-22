"use client";

import { Fragment, useCallback, useEffect, useMemo, useRef, useState } from "react";

import AttachmentsPanel from "@/components/attachments-panel";
import Combobox from "@/components/combobox";
import Pagination from "@/components/pagination";
import PurchaseSearch from "@/components/purchase-search";
import { api, apiAll, errorMessage } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { optionLabel, toOptions, withSelectedOptions } from "@/lib/options";
import { canWrite } from "@/lib/permissions";
import { purchaseLineEditState } from "@/lib/purchase-edit";
import { EMPTY_PURCHASE_FILTERS, purchaseSearchParams, type PurchaseFilters } from "@/lib/purchase-search";

interface Option {
  id: number;
  name?: string;
  code?: string;
  storage_specs?: string;
  is_active?: boolean;
  can_purchase?: boolean;
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
  collected?: string;
  refunded?: string;
  can_correct?: boolean;
  correction_block_reason?: string;
  minimum_quantity?: string;
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
  refunded: string;
  can_correct: boolean;
  correction_block_reason: string;
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
  const [filters, setFilters] = useState<PurchaseFilters>(EMPTY_PURCHASE_FILTERS);
  const [query, setQuery] = useState({ filters: EMPTY_PURCHASE_FILTERS, page: 1 });
  const page = query.page;
  const queryString = purchaseSearchParams(query.filters, page);
  const intendedQuery = useRef(queryString);
  const latestRequest = useRef(0);
  const [loading, setLoading] = useState(true);
  const [refreshKey, setRefreshKey] = useState(0);
  const [optionsError, setOptionsError] = useState("");
  const [totals, setTotals] = useState<Record<string, string>>({});
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

  const productOptions = useMemo(() => toOptions(products.filter((item) => item.is_active !== false)), [products]);
  const filterLabel = (item: Option) => `${optionLabel(item)}${item.is_active === false ? " (inactive)" : ""}`;
  const filterProducts = useMemo(() => toOptions(products, filterLabel), [products]);
  const filterLocations = useMemo(() => toOptions(locations, filterLabel), [locations]);
  const filterSuppliers = useMemo(() => toOptions(suppliers, filterLabel), [suppliers]);
  const locationOptions = useMemo(() => withSelectedOptions(toOptions(locations.filter((item) => item.is_active !== false && item.can_purchase !== false)), editing
    ? [{ value: String(editing.location), label: editing.location_name }] : []), [locations, editing]);
  const supplierOptions = useMemo(() => withSelectedOptions(toOptions(suppliers.filter((item) => item.is_active !== false)), editing
    ? [{ value: String(editing.supplier), label: editing.supplier_name }] : []), [suppliers, editing]);
  // Currencies are picked by their code, as they always have been.
  const currencyOptions = useMemo(
    () => toOptions(currencies, (currency) => currency.code ?? currency.name ?? `#${currency.id}`),
    [currencies],
  );

  function changeFilters(next: PurchaseFilters) {
    setFilters(next);
    intendedQuery.current = purchaseSearchParams(next);
    if (intendedQuery.current !== queryString) {
      latestRequest.current += 1;
      setLoading(true);
    } else {
      // Returning to the current query before debounce must restart cancelled loads.
      setRefreshKey((value) => value + 1);
    }
    setError("");
    setExpanded(null);
  }

  // Set filters and page together: changing filters never requests an old page.
  useEffect(() => {
    const timer = window.setTimeout(() => setQuery((current) => (
      current.filters === filters && current.page === 1 ? current : { filters, page: 1 }
    )), 300);
    return () => window.clearTimeout(timer);
  }, [filters]);

  const load = useCallback(async () => {
    if (queryString !== intendedQuery.current) return;
    const request = ++latestRequest.current;
    setLoading(true);
    setError("");
    const params = new URLSearchParams(queryString);
    if (params.get("date_from") && params.get("date_to") && params.get("date_from")! > params.get("date_to")!) {
      setError("End date must be on or after start date.");
      setRows([]); setCount(0); setTotals({}); setLoading(false);
      return;
    }
    try {
      const data = await api<ListResponse>(`/api/v1/purchases/${queryString ? `?${queryString}` : ""}`);
      if (request !== latestRequest.current || queryString !== intendedQuery.current) return;
      setRows(data.results);
      setCount(data.count);
      setTotals(data.totals ?? {});
    } catch (err) {
      if (request !== latestRequest.current || queryString !== intendedQuery.current) return;
      setError(errorMessage(err)); setRows([]); setCount(0); setTotals({});
    } finally {
      if (request === latestRequest.current) setLoading(false);
    }
  }, [queryString]);

  useEffect(() => {
    void load();
    return () => { latestRequest.current += 1; };
  }, [load, refreshKey]);

  const loadChoices = useCallback(async () => {
    setOptionsError("");
    const results = await Promise.allSettled([
      apiAll<Option>("/api/v1/products/"),
      apiAll<Option>("/api/v1/locations/"),
      apiAll<Option>("/api/v1/suppliers/"),
      apiAll<Option>("/api/v1/currencies/?is_active=true"),
    ]);
    const setters = [setProducts, setLocations, setSuppliers, setCurrencies];
    results.forEach((result, index) => {
      if (result.status === "fulfilled") setters[index](result.value);
    });
    if (results.some((result) => result.status === "rejected")) {
      setOptionsError("Some filter choices could not be loaded.");
    }
  }, []);

  useEffect(() => { void loadChoices(); }, [loadChoices]);

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
        refunded: line.refunded,
        can_correct: line.can_correct,
        correction_block_reason: line.correction_block_reason,
        minimum_quantity: Math.max(0.01, Number(line.quantity) - Number(line.pending)).toFixed(2),
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
      <div className="mb-5 flex flex-wrap items-center justify-between gap-3">
        <div><h1 className="text-2xl font-semibold tracking-tight">Purchases</h1>
          <p className="mt-1 text-sm text-muted">Find invoices and keep track of what’s received and pending.</p></div>
        {writable && <button className="inline-flex items-center gap-2 rounded-lg bg-primary px-4 py-2.5 text-sm font-medium text-on-primary hover:bg-primary-strong" onClick={openCreate}><span aria-hidden="true">+</span> New Purchase</button>}
      </div>

      <PurchaseSearch filters={filters} onChange={changeFilters}
        suppliers={filterSuppliers} locations={filterLocations} products={filterProducts}
        loading={loading} count={count} page={page} error={error}
        optionsError={optionsError} onRetryOptions={() => void loadChoices()} />

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
            <div className="text-lg font-semibold">{loading || error ? "—" : value ?? "—"}</div>
          </div>
        ))}
      </div>

      {error && <p role="alert" className="mb-3 text-sm text-danger">{error} <button className="underline" onClick={() => void load()}>Retry</button></p>}

      <div aria-busy={loading} className="overflow-x-auto rounded-lg border border-edge bg-surface">
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
            {!loading && !error && rows.map((purchase) => (
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
            {loading && <tr><td colSpan={7} className="px-4 py-12 text-center text-sm text-muted"><span className="mr-2 inline-block h-4 w-4 animate-spin rounded-full border-2 border-edge border-t-primary align-middle motion-reduce:animate-none" />Loading purchases…</td></tr>}
            {!loading && rows.length === 0 && <tr><td className="px-4 py-12 text-center" colSpan={7}>
              <p className="font-medium text-ink-2">{error ? "Purchases could not be loaded" : "No matching purchases"}</p>
              <p className="mt-1 text-sm text-muted">{error ? "Try loading the list again." : "Try a different search or remove a filter to see more invoices."}</p>
              {!error && <button className="mt-3 text-sm font-medium text-primary hover:underline" onClick={() => changeFilters({ ...EMPTY_PURCHASE_FILTERS })}>Clear search and filters</button>}
            </td></tr>}
          </tbody>
        </table>
      </div>

      {!loading && !error && <Pagination page={page} count={count} onPage={(nextPage) => {
        intendedQuery.current = purchaseSearchParams(query.filters, nextPage);
        latestRequest.current += 1; setLoading(true); setExpanded(null);
        setQuery({ ...query, page: nextPage });
      }} />}

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
                <Combobox
                  className={inputCls}
                  required
                  disabled={Boolean(editing)}
                  options={locationOptions}
                  value={header.location}
                  onChange={(next) => setHeader({ ...header, location: next })}
                />
              </label>
              <label className="block text-sm">
                <span className="mb-1 block font-medium text-ink-2">
                  Supplier/party <span className="text-danger">*</span>
                </span>
                <Combobox
                  className={inputCls}
                  required
                  options={supplierOptions}
                  value={header.supplier}
                  onChange={(next) => setHeader({ ...header, supplier: next })}
                />
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
              {editing && (
                <p className="mb-3 text-xs text-muted">
                  You can correct products, unit prices and remove lines while received stock
                  has no downstream movements. Currency, exchange rate and GST stay fixed after collection.
                </p>
              )}
              <div className="space-y-3">
                {lines.map((line, index) => {
                  const { correctionLocked, ratesLocked, reason } = purchaseLineEditState(line);
                  const original = editing?.lines.find((item) => item.id === line.id);
                  const lineProducts = withSelectedOptions(productOptions, original
                    ? [{ value: String(original.product), label: original.product_name }] : []);
                  const lineCurrencies = withSelectedOptions(currencyOptions, original
                    ? [{ value: String(original.currency), label: original.currency_code }] : []);
                  return (
                    <div
                      key={line.id ?? `new-${index}`}
                      className="grid gap-2 rounded border border-edge p-3 sm:grid-cols-2 lg:grid-cols-7"
                    >
                      <label className="block text-xs lg:col-span-2">
                        <span className="mb-1 block font-medium text-ink-2">
                          Product *
                        </span>
                        <Combobox
                          className={inputCls}
                          required
                          disabled={correctionLocked}
                          options={lineProducts}
                          value={line.product}
                          onChange={(value) => {
                            const next = [...lines];
                            next[index] = { ...line, product: value };
                            setLines(next);
                          }}
                        />
                      </label>
                      <label className="block text-xs">
                        <span className="mb-1 block font-medium text-ink-2">Qty *</span>
                        <input
                          className={inputCls}
                          type="number"
                          step="any"
                          min={line.minimum_quantity ?? "0.01"}
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
                          disabled={correctionLocked}
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
                        <Combobox
                          className={inputCls}
                          required
                          disabled={ratesLocked}
                          options={lineCurrencies}
                          value={line.currency}
                          onChange={(value) => {
                            const next = [...lines];
                            next[index] = { ...line, currency: value };
                            setLines(next);
                          }}
                        />
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
                          disabled={ratesLocked}
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
                            disabled={ratesLocked}
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
                        {lines.length > 1 && !correctionLocked && (
                          <button
                            type="button"
                            className="text-xs text-danger hover:underline"
                            onClick={() => setLines(lines.filter((_, i) => i !== index))}
                          >
                            Remove
                          </button>
                        )}
                      </div>
                      {line.id && (
                        <p className="text-xs text-muted sm:col-span-2 lg:col-span-7">
                          Collected: {line.collected}. Minimum quantity: {line.minimum_quantity}.
                        </p>
                      )}
                      {reason && (
                        <p className="text-xs text-warning sm:col-span-2 lg:col-span-7">{reason}</p>
                      )}
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
