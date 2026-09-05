import assert from "node:assert/strict";
import test from "node:test";

import {
  firstMatchingIndex,
  optionLabel,
  rankOptions,
  toOptions,
} from "../lib/options.ts";

/** Alphabetical, the way the products endpoint returns them. */
const CATALOGUE = toOptions([
  { id: 1, name: "Canon EOS R6" },
  { id: 2, name: "iPhone 15 Pro", storage_specs: "256GB" },
  { id: 3, name: "iPhone 15 Pro", storage_specs: "512GB" },
  { id: 4, name: "JBL Flip 6" },
  { id: 5, name: "Kingston SSD", storage_specs: "1TB" },
  { id: 6, name: "Samsung Galaxy S24" },
  { id: 7, name: "Sony WH-1000XM5" },
  { id: 8, name: "Starlink Mini" },
  { id: 9, name: "Starlink Standard Kit" },
]);

const labels = (rows) => rows.map((row) => row.label);

test("a single letter still jumps to the first entry starting with it", () => {
  // The behaviour users relied on from the native <select> is preserved.
  assert.equal(rankOptions(CATALOGUE, "s")[0].label, "Samsung Galaxy S24");
});

test("typing the whole word finds it instead of landing on the last letter", () => {
  // The reported bug: <select> type-ahead expired between keystrokes, so
  // "starlink" ended as a search for "k" and selected Kingston SSD.
  const matches = rankOptions(CATALOGUE, "starlink");

  assert.deepEqual(labels(matches), ["Starlink Mini", "Starlink Standard Kit"]);
  assert.ok(!labels(matches).includes("Kingston SSD"));
});

test("every prefix of a word keeps that word's entries at the top", () => {
  // Typing letter by letter must never wander off to another product.
  for (const prefix of ["s", "st", "sta", "star", "starl", "starli", "starlin", "starlink"]) {
    assert.equal(
      rankOptions(CATALOGUE, prefix)[0].label.startsWith("S"),
      true,
      `"${prefix}" should stay on an S entry`,
    );
  }
  assert.equal(rankOptions(CATALOGUE, "st")[0].label, "Starlink Mini");
});

test("matching is case-insensitive and works mid-label", () => {
  assert.deepEqual(labels(rankOptions(CATALOGUE, "STARLINK MINI")), ["Starlink Mini"]);
  assert.deepEqual(labels(rankOptions(CATALOGUE, "galaxy")), ["Samsung Galaxy S24"]);
  assert.deepEqual(labels(rankOptions(CATALOGUE, "1000")), ["Sony WH-1000XM5"]);
});

test("words can be typed in any order, so specs narrow a repeated name", () => {
  assert.deepEqual(labels(rankOptions(CATALOGUE, "iphone 512")), ["iPhone 15 Pro 512GB"]);
  assert.deepEqual(labels(rankOptions(CATALOGUE, "512 pro")), ["iPhone 15 Pro 512GB"]);
});

test("an exact label outranks longer labels containing it", () => {
  const options = toOptions([
    { id: 1, name: "Starlink Standard Kit" },
    { id: 2, name: "Starlink" },
  ]);

  assert.equal(rankOptions(options, "starlink")[0].label, "Starlink");
});

test("no match returns nothing rather than an arbitrary entry", () => {
  assert.deepEqual(rankOptions(CATALOGUE, "zzz"), []);
});

test("an empty query keeps the endpoint's own ordering", () => {
  assert.deepEqual(rankOptions(CATALOGUE, ""), CATALOGUE);
  assert.deepEqual(rankOptions(CATALOGUE, "   "), CATALOGUE);
});

test("storage/specs are part of the label, so same-named products differ", () => {
  // FR-018/FR-019 allow one name with different specs; a dropdown showing only
  // the name would offer two identical rows.
  assert.equal(optionLabel({ id: 2, name: "iPhone 15 Pro", storage_specs: "256GB" }), "iPhone 15 Pro 256GB");
  assert.equal(optionLabel({ id: 4, name: "JBL Flip 6" }), "JBL Flip 6");
  assert.equal(optionLabel({ id: 7, code: "AED", name: null }), "AED");
  assert.equal(optionLabel({ id: 9, username: "ahmed" }), "ahmed");
  assert.equal(optionLabel({ id: 11 }), "#11");
});

test("short lists can still be jumped through by first letter", () => {
  const buckets = toOptions([
    { id: "PHYSICAL", name: "Physical" },
    { id: "PENDING", name: "Pending" },
    { id: "IN_TRANSIT", name: "In transit" },
  ]);

  assert.equal(firstMatchingIndex(buckets, "i"), 2);
  assert.equal(firstMatchingIndex(buckets, "P"), 0);
  assert.equal(firstMatchingIndex(buckets, "z"), -1);
});
