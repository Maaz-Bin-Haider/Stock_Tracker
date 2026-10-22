"use client";

import { useState } from "react";

import Combobox from "@/components/combobox";
import type { ChoiceOption } from "@/lib/options";
import {
  EMPTY_PURCHASE_FILTERS, PURCHASE_SORTS, PURCHASE_STATUSES, purchaseDateRange,
  SEARCH_SCOPES, type PurchaseFilters,
} from "@/lib/purchase-search";

function SearchIcon({ className = "h-5 w-5" }: { className?: string }) {
  return <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" aria-hidden="true"><circle cx="10.5" cy="10.5" r="6.5" /><path d="m16 16 4.5 4.5" /></svg>;
}

const control = "w-full rounded-lg border border-edge bg-surface px-3 py-2 text-sm text-ink focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/15";
const smallButton = "rounded-lg border border-edge px-3 py-1.5 text-xs font-medium text-ink-2 hover:border-primary hover:text-primary focus-visible:outline-2 focus-visible:outline-primary";

export default function PurchaseSearch({ filters, onChange, suppliers, locations, products, loading, count, page, error, optionsError, onRetryOptions }: {
  filters: PurchaseFilters;
  onChange: (next: PurchaseFilters) => void;
  suppliers: ChoiceOption[];
  locations: ChoiceOption[];
  products: ChoiceOption[];
  loading: boolean;
  count: number;
  page: number;
  error: string;
  optionsError: string;
  onRetryOptions: () => void;
}) {
  const [showFilters, setShowFilters] = useState(false);
  const update = (changes: Partial<PurchaseFilters>) => onChange({ ...filters, ...changes });
  const chips: { key: keyof PurchaseFilters | "dates"; label: string }[] = [];
  const choiceLabel = (options: ChoiceOption[], value: string) => options.find((option) => option.value === value)?.label ?? `#${value}`;
  if (filters.search.trim()) chips.push({ key: "search", label: `${SEARCH_SCOPES.find((scope) => scope.value === filters.search_in)?.label}: ${filters.search.trim()}` });
  if (filters.status) chips.push({ key: "status", label: PURCHASE_STATUSES.find((status) => status.value === filters.status)?.label ?? filters.status });
  if (filters.supplier) chips.push({ key: "supplier", label: `Supplier: ${choiceLabel(suppliers, filters.supplier)}` });
  if (filters.location) chips.push({ key: "location", label: `Location: ${choiceLabel(locations, filters.location)}` });
  if (filters.product) chips.push({ key: "product", label: `Product: ${choiceLabel(products, filters.product)}` });
  if (filters.date_from || filters.date_to) chips.push({ key: "dates", label: `${filters.date_from || "Any date"} → ${filters.date_to || "Any end date"}` });
  const advancedCount = [filters.supplier, filters.location, filters.product, filters.date_from || filters.date_to].filter(Boolean).length;
  const hasChanges = chips.length > 0 || filters.search_in !== "all" || filters.ordering !== EMPTY_PURCHASE_FILTERS.ordering;
  const rangeError = filters.date_from && filters.date_to && filters.date_from > filters.date_to;

  return (
    <section aria-label="Purchase search and filters" className="mb-5 min-w-0 rounded-xl border border-edge bg-surface">
      <div role="search" className="p-4 sm:p-5">
        <div className="flex flex-col gap-3 sm:flex-row">
          <div className="flex min-w-0 flex-1 items-center rounded-xl border border-edge bg-surface-2 px-3 transition focus-within:border-primary focus-within:ring-2 focus-within:ring-primary/15">
            <SearchIcon className="mr-3 h-5 w-5 shrink-0 text-muted" />
            <label className="sr-only" htmlFor="purchase-search">Search purchases</label>
            <input id="purchase-search" type="search" autoComplete="off" value={filters.search}
              onChange={(event) => update({ search: event.target.value })}
              placeholder={filters.search_in === "all" ? "Search invoice, product, SKU, supplier…" : `Search ${SEARCH_SCOPES.find((scope) => scope.value === filters.search_in)?.label.toLowerCase()}…`}
              className="min-w-0 flex-1 bg-transparent py-3 text-sm text-ink outline-none placeholder:text-muted [&::-webkit-search-cancel-button]:hidden" />
            {filters.search && <button type="button" aria-label="Clear search" onClick={() => update({ search: "" })} className="mx-1 rounded p-1 text-muted hover:bg-surface hover:text-ink">×</button>}
            <div className="ml-1 w-28 shrink-0 border-l border-edge pl-2 sm:w-36">
              <label htmlFor="purchase-search-scope" className="sr-only">Search in</label>
              <Combobox id="purchase-search-scope" value={filters.search_in} onChange={(search_in) => update({ search_in })} options={SEARCH_SCOPES} className="w-full border-0 bg-transparent py-2 pl-1 pr-6 text-xs text-ink-2 focus:outline-none" />
            </div>
          </div>
          <button type="button" aria-expanded={showFilters} aria-controls="purchase-advanced-filters" onClick={() => setShowFilters(!showFilters)}
            className={`inline-flex items-center justify-center gap-2 rounded-xl border px-4 py-3 text-sm font-medium transition focus-visible:outline-2 focus-visible:outline-primary ${showFilters || advancedCount ? "border-primary bg-primary-soft text-primary" : "border-edge text-ink-2 hover:bg-surface-2"}`}>
            <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" aria-hidden="true"><path d="M4 7h16M4 17h16M8 4v6M16 14v6" /></svg>
            Filters {advancedCount > 0 && <span className="rounded-md bg-primary px-1.5 py-0.5 text-xs text-on-primary">{advancedCount}</span>}
          </button>
        </div>
        <div className="mt-4 flex flex-wrap items-center gap-1.5" aria-label="Invoice status">
          {PURCHASE_STATUSES.map((status) => <button key={status.value} type="button" aria-pressed={filters.status === status.value} onClick={() => update({ status: status.value })}
            className={`rounded-full px-3 py-1.5 text-xs font-medium transition focus-visible:outline-2 focus-visible:outline-primary ${filters.status === status.value ? "bg-primary text-on-primary" : "bg-surface-2 text-ink-2 hover:bg-primary-soft hover:text-primary"}`}>{status.label}</button>)}
        </div>
      </div>

      {showFilters && <div id="purchase-advanced-filters" className="border-t border-edge bg-surface-2/60 p-4 sm:px-5">
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
          {[
            { key: "supplier", label: "Supplier", options: suppliers, placeholder: "All suppliers" },
            { key: "location", label: "Purchase location", options: locations, placeholder: "All locations" },
            { key: "product", label: "Product", options: products, placeholder: "All products" },
          ].map(({ key, label, options, placeholder }) => <div key={key}>
            <label htmlFor={`purchase-filter-${key}`} className="mb-1.5 block text-xs font-medium text-ink-2">{label}</label>
            <Combobox id={`purchase-filter-${key}`} value={filters[key as "supplier" | "location" | "product"]} onChange={(value) => update({ [key]: value })} options={options} allowEmpty placeholder={placeholder} className={control} />
          </div>)}
        </div>
        {optionsError && <p role="alert" className="mt-3 text-xs text-danger">{optionsError} <button type="button" onClick={onRetryOptions} className="underline">Retry choices</button></p>}
        <div className="mt-4 grid items-end gap-4 sm:grid-cols-2 xl:grid-cols-3">
          <div><label htmlFor="purchase-date-from" className="mb-1.5 block text-xs font-medium text-ink-2">From purchase date</label><input id="purchase-date-from" type="date" value={filters.date_from} max={filters.date_to || undefined} onChange={(event) => update({ date_from: event.target.value })} className={control} /></div>
          <div><label htmlFor="purchase-date-to" className="mb-1.5 block text-xs font-medium text-ink-2">To purchase date</label><input id="purchase-date-to" type="date" value={filters.date_to} min={filters.date_from || undefined} onChange={(event) => update({ date_to: event.target.value })} className={control} /></div>
          <div className="flex flex-wrap gap-2 pb-0.5">
            <button type="button" className={smallButton} onClick={() => update({ date_from: "", date_to: "" })}>All dates</button>
            {([ ["today", "Today"], ["week", "Last 7 days"], ["month", "This month"] ] as const).map(([preset, label]) => <button key={preset} type="button" className={smallButton} onClick={() => update(purchaseDateRange(preset))}>{label}</button>)}
          </div>
        </div>
        <p className={`mt-2 text-xs ${rangeError ? "text-danger" : "text-muted"}`} role={rangeError ? "alert" : undefined}>{rangeError ? "End date must be on or after start date." : "Date shortcuts use the Dubai business date. Date limits are inclusive."}</p>
      </div>}

      {chips.length > 0 && <div className="flex flex-wrap gap-2 border-t border-edge px-4 py-3 sm:px-5" aria-label="Active filters">
        {chips.map((chip) => <button type="button" key={chip.key} aria-label={`Remove filter: ${chip.label}`} onClick={() => chip.key === "dates" ? update({ date_from: "", date_to: "" }) : update({ [chip.key]: "" })}
          className="inline-flex max-w-full items-center gap-2 rounded-lg border border-edge bg-surface-2 px-2.5 py-1 text-xs text-ink-2 hover:border-primary hover:text-primary"><span className="truncate">{chip.label}</span><span aria-hidden="true">×</span></button>)}
      </div>}

      <div className="flex flex-wrap items-center justify-between gap-3 border-t border-edge px-4 py-3 sm:px-5">
        <div className="flex items-center gap-3 text-xs text-muted">
          <span role="status" aria-live="polite">{error || rangeError ? "Results unavailable" : loading ? "Finding purchases…" : `${count === 0 ? "0" : `${(page - 1) * 50 + 1}–${Math.min(page * 50, count)}`} of ${count} ${count === 1 ? "invoice" : "invoices"}`}{chips.length > 0 && !loading && !error && !rangeError ? " · Filtered" : ""}</span>
          {hasChanges && <button type="button" onClick={() => onChange({ ...EMPTY_PURCHASE_FILTERS })} className="font-medium text-primary hover:underline">Reset all</button>}
        </div>
        <div className="flex items-center gap-2"><label htmlFor="purchase-sort" className="text-xs text-muted">Sort by</label><Combobox id="purchase-sort" value={filters.ordering} onChange={(ordering) => update({ ordering })} options={PURCHASE_SORTS} wrapperClassName="w-44" className="w-full rounded-lg border border-edge bg-surface px-2.5 py-1.5 text-xs text-ink-2 focus:outline-primary" /></div>
      </div>
    </section>
  );
}
