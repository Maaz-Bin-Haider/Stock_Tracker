import assert from "node:assert/strict";
import test from "node:test";

import { withSelectedOptions } from "../lib/options.ts";
import { purchaseLineEditState } from "../lib/purchase-edit.ts";

test("received unsold stock can correct product/price while frozen rates stay fixed", () => {
  const state = purchaseLineEditState({ id: 1, collected: "4.00", can_correct: true });
  assert.equal(state.correctionLocked, false);
  assert.equal(state.ratesLocked, true);
});

test("a refund-only dependency disables correction and supplies its explanation", () => {
  const state = purchaseLineEditState({
    id: 1, collected: "0.00", refunded: "2.00", can_correct: false,
    correction_block_reason: "This line has a cancellation.",
  });
  assert.equal(state.correctionLocked, true);
  assert.equal(state.ratesLocked, true);
  assert.equal(state.reason, "This line has a cancellation.");
});

test("missing eligibility from an older API does not unlock a received line", () => {
  assert.equal(purchaseLineEditState({ id: 1, collected: "4.00" }).correctionLocked, true);
  assert.equal(purchaseLineEditState({ id: 1, collected: "0.00" }).correctionLocked, false);
});

test("historical selection remains visible without overriding a current catalogue label", () => {
  const options = [{ value: "1", label: "Current product name" }];
  assert.deepEqual(withSelectedOptions(options, [
    { value: "1", label: "Old label" }, { value: "2", label: "Archived selected product" },
    { value: "2", label: "Duplicate" },
  ]), [{ value: "1", label: "Current product name" }, { value: "2", label: "Archived selected product" }]);
  assert.deepEqual(options, [{ value: "1", label: "Current product name" }]);
});
