import assert from "node:assert/strict";
import test from "node:test";

import { collectPaginated } from "../lib/pagination.ts";

test("collectPaginated loads all products beyond the first 50-item API page", async () => {
  const products = Array.from({ length: 205 }, (_, index) => ({
    id: index + 1,
    name: `Product ${String(index + 1).padStart(3, "0")}`,
  }));
  const requested = [];

  const rows = await collectPaginated("/api/v1/products/?is_active=true", async (path) => {
    requested.push(path);
    const url = new URL(path, "https://stock.example");
    const page = Number(url.searchParams.get("page") ?? "1");
    const start = (page - 1) * 50;
    const nextPage = start + 50 < products.length ? page + 1 : null;
    return {
      results: products.slice(start, start + 50),
      next: nextPage
        ? `https://stock.example/api/v1/products/?is_active=true&page=${nextPage}`
        : null,
    };
  });

  assert.equal(rows.length, 205);
  assert.deepEqual(rows.at(-1), { id: 205, name: "Product 205" });
  assert.equal(requested.length, 5);
  assert.equal(requested[1], "/api/v1/products/?is_active=true&page=2");
});

test("collectPaginated rejects a repeated next link instead of looping forever", async () => {
  await assert.rejects(
    collectPaginated("/api/v1/products/", async () => ({
      results: [],
      next: "/api/v1/products/",
    })),
    /Pagination loop detected/,
  );
});
