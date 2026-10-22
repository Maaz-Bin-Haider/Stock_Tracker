export const PURCHASE_STATUSES = [
  { value: "", label: "All invoices" },
  { value: "PENDING", label: "Pending" },
  { value: "PARTIALLY_RECEIVED", label: "Partially received" },
  { value: "FULLY_COLLECTED", label: "Fully collected" },
  { value: "CANCELLED", label: "Cancelled" },
  { value: "REFUNDED", label: "Refunded" },
];

export const SEARCH_SCOPES = [
  { value: "all", label: "All fields" },
  { value: "invoice", label: "Invoice number" },
  { value: "product", label: "Product / SKU" },
  { value: "supplier", label: "Supplier" },
  { value: "location", label: "Location" },
  { value: "notes", label: "Notes" },
];

export const PURCHASE_SORTS = [
  { value: "-purchase_date", label: "Newest purchases" },
  { value: "purchase_date", label: "Oldest purchases" },
  { value: "invoice_no", label: "Invoice number A–Z" },
  { value: "supplier__name", label: "Supplier A–Z" },
];

export interface PurchaseFilters {
  search: string;
  search_in: string;
  status: string;
  supplier: string;
  location: string;
  product: string;
  date_from: string;
  date_to: string;
  ordering: string;
}

export const EMPTY_PURCHASE_FILTERS: PurchaseFilters = {
  search: "", search_in: "all", status: "", supplier: "", location: "", product: "",
  date_from: "", date_to: "", ordering: "-purchase_date",
};

export function purchaseSearchParams(filters: PurchaseFilters, page = 1): string {
  const params = new URLSearchParams();
  for (const [key, value] of Object.entries(filters)) {
    const cleaned = value.trim();
    if (!cleaned || (key === "search_in" && (!filters.search.trim() || cleaned === "all"))
      || (key === "ordering" && cleaned === "-purchase_date")) continue;
    params.set(key, cleaned);
  }
  if (page > 1) params.set("page", String(page));
  return params.toString();
}

export function purchaseDateRange(preset: "today" | "week" | "month", now = new Date()) {
  const parts = new Intl.DateTimeFormat("en-CA", {
    timeZone: "Asia/Dubai", year: "numeric", month: "2-digit", day: "2-digit",
  }).formatToParts(now);
  const part = (name: string) => Number(parts.find((item) => item.type === name)?.value);
  const end = new Date(Date.UTC(part("year"), part("month") - 1, part("day")));
  const start = new Date(end);
  if (preset === "week") start.setUTCDate(start.getUTCDate() - 6);
  if (preset === "month") start.setUTCDate(1);
  return { date_from: start.toISOString().slice(0, 10), date_to: end.toISOString().slice(0, 10) };
}
