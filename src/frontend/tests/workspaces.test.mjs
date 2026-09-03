import assert from "node:assert/strict";
import test from "node:test";

import {
  CURRENT_WORKSPACE_ID,
  ICON_PATHS,
  WORKSPACES,
  currentWorkspace,
  otherWorkspaces,
} from "../lib/workspaces.ts";

const ACCENTS = ["blue", "emerald", "amber", "violet"];

test("the switcher offers every workspace except this one", () => {
  const others = otherWorkspaces();

  assert.ok(others.length >= 1, "there should be somewhere to switch to");
  assert.ok(
    others.every((w) => w.id !== CURRENT_WORKSPACE_ID),
    "the current workspace must never be offered as a destination",
  );
  assert.equal(others.length, WORKSPACES.length - 1);
});

test("this application knows which workspace it is", () => {
  assert.equal(currentWorkspace().id, CURRENT_WORKSPACE_ID);
  assert.equal(currentWorkspace().id, "stock");
});

test("every workspace declares an icon and accent the CSS actually defines", () => {
  for (const workspace of WORKSPACES) {
    assert.ok(
      ICON_PATHS[workspace.icon],
      `${workspace.id} uses icon "${workspace.icon}", which has no paths`,
    );
    assert.ok(
      ACCENTS.includes(workspace.accent),
      `${workspace.id} uses accent "${workspace.accent}", which globals.css does not define`,
    );
    assert.ok(workspace.url, `${workspace.id} has no URL`);
    assert.ok(workspace.name && workspace.tagline, `${workspace.id} is missing copy`);
    assert.ok(workspace.modules.length > 0, `${workspace.id} lists no modules`);
  }
});

test("workspace ids are unique, so React keys and lookups stay stable", () => {
  const ids = WORKSPACES.map((w) => w.id);
  assert.equal(new Set(ids).size, ids.length);
});

test("the ERP is not advertised as signing the employee in", () => {
  // Trust is one-directional: this system never asserts identity to the ERP,
  // so the transition must not promise a session it cannot create.
  const erp = WORKSPACES.find((w) => w.id === "erp");
  assert.ok(erp, "the ERP should be in the registry");
  assert.equal(erp.signsIn, false);
});
