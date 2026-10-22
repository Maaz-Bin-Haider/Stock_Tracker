import assert from "node:assert/strict";
import test from "node:test";
import { EMPTY_PURCHASE_FILTERS, purchaseDateRange, purchaseSearchParams } from "../lib/purchase-search.ts";

test("default query and empty search scope do not add spurious filters", () => {
  assert.equal(purchaseSearchParams(EMPTY_PURCHASE_FILTERS), "");
  assert.equal(purchaseSearchParams({ ...EMPTY_PURCHASE_FILTERS, search_in: "product" }), "");
});

test("all filters combine safely and pagination preserves them", () => {
  const filters = { ...EMPTY_PURCHASE_FILTERS, search: "  Phone & Case  ", search_in: "product", status: "PENDING", supplier: "3", location: "2", product: "8", date_from: "2026-10-01", date_to: "2026-10-22", ordering: "purchase_date" };
  const params = new URLSearchParams(purchaseSearchParams(filters, 2));
  assert.equal(params.get("search"), "Phone & Case");
  assert.equal(params.get("search_in"), "product");
  assert.equal(params.get("supplier"), "3");
  assert.equal(params.get("page"), "2");
  assert.equal(params.get("date_to"), "2026-10-22");
  assert.equal(params.get("ordering"), "purchase_date");
});

test("date shortcuts respect Dubai midnight and include exactly seven dates", () => {
  const now = new Date("2026-10-31T20:30:00Z");
  assert.deepEqual(purchaseDateRange("today", now), { date_from: "2026-11-01", date_to: "2026-11-01" });
  assert.deepEqual(purchaseDateRange("week", now), { date_from: "2026-10-26", date_to: "2026-11-01" });
  assert.deepEqual(purchaseDateRange("month", now), { date_from: "2026-11-01", date_to: "2026-11-01" });
});
