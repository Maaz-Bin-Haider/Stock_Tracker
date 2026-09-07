import assert from "node:assert/strict";
import test from "node:test";

import { buildPayload } from "../lib/resource-form.ts";

/** The GST Rates settings form (app/(app)/settings/[resource]/page.tsx). */
const GST_RATE_FIELDS = [
  { name: "location", label: "Location", required: true, optionsEndpoint: "/api/v1/locations/" },
  { name: "rate", label: "Rate (%)", type: "number", required: true },
  { name: "effective_from", label: "Effective from", type: "date", required: true },
  { name: "effective_to", label: "Effective to", type: "date" },
  { name: "is_active", label: "Active", type: "checkbox" },
];

test("clearing an optional date sends null so PATCH actually clears it", () => {
  // The production incident: a GST rate was given an end date, and every
  // attempt to remove it saved successfully while changing nothing, because
  // the cleared field was dropped from the PATCH body.
  const payload = buildPayload(GST_RATE_FIELDS, {
    location: "2",
    rate: "10.00",
    effective_from: "2026-01-01",
    effective_to: "",
    is_active: true,
  });

  assert.ok("effective_to" in payload, "a cleared date must be sent, not omitted");
  assert.equal(payload.effective_to, null);
});

test("a filled optional date is still sent as its value", () => {
  const payload = buildPayload(GST_RATE_FIELDS, {
    location: "2",
    rate: "10.00",
    effective_from: "2026-01-01",
    effective_to: "2026-09-07",
    is_active: true,
  });

  assert.equal(payload.effective_to, "2026-09-07");
});

test("foreign keys go back as numeric ids and checkboxes as booleans", () => {
  const payload = buildPayload(GST_RATE_FIELDS, {
    location: "2",
    rate: "10.00",
    effective_from: "2026-01-01",
    effective_to: "",
    is_active: false,
  });

  assert.equal(payload.location, 2);
  assert.equal(typeof payload.location, "number");
  assert.equal(payload.is_active, false);
  assert.equal(payload.rate, "10.00");
});

test("a blank password still means 'keep the current one'", () => {
  const fields = [
    { name: "username", label: "Username", required: true },
    { name: "password", label: "Password", type: "password" },
  ];

  const payload = buildPayload(fields, { username: "saqib", password: "" });

  assert.ok(!("password" in payload), "an empty password must stay out of the payload");
  assert.equal(payload.username, "saqib");
});

test("a static choice keeps its string value rather than becoming a number", () => {
  const fields = [
    {
      name: "role",
      label: "Role",
      type: "select",
      required: true,
      options: [{ value: "ADMIN", label: "Admin" }],
    },
  ];

  assert.equal(buildPayload(fields, { role: "ADMIN" }).role, "ADMIN");
});

test("an optional choice left empty clears rather than sticking", () => {
  const fields = [
    { name: "category", label: "Category", optionsEndpoint: "/api/v1/categories/" },
  ];

  const payload = buildPayload(fields, { category: "" });

  assert.ok("category" in payload);
  assert.equal(payload.category, null);
});
