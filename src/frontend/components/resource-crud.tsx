"use client";

import { useCallback, useEffect, useState } from "react";

import Pagination from "@/components/pagination";
import { api, errorMessage } from "@/lib/api";

export type FieldType =
  | "text"
  | "number"
  | "date"
  | "checkbox"
  | "password"
  | "select"
  | "textarea";

export interface FieldDef {
  name: string;
  label: string;
  type?: FieldType;
  required?: boolean;
  /** Static choices (e.g. roles). */
  options?: { value: string; label: string }[];
  /** Load choices from a list endpoint (foreign keys). */
  optionsEndpoint?: string;
  optionLabelKey?: string;
  defaultValue?: string | boolean;
}

export interface ColumnDef {
  key: string;
  label: string;
}

interface Row {
  id: number;
  [key: string]: unknown;
}

interface ListResponse {
  count: number;
  results: Row[];
}

type FormValues = Record<string, string | boolean>;

function formatCell(value: unknown): string {
  if (value === null || value === undefined || value === "") return "—";
  if (typeof value === "boolean") return value ? "Yes" : "No";
  return String(value);
}

export default function ResourceCrud({
  title,
  endpoint,
  columns,
  fields,
  canWrite,
  allowDelete = true,
}: {
  title: string;
  endpoint: string;
  columns: ColumnDef[];
  fields: FieldDef[];
  canWrite: boolean;
  allowDelete?: boolean;
}) {
  const [rows, setRows] = useState<Row[]>([]);
  const [count, setCount] = useState(0);
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(1);
  const [editing, setEditing] = useState<Row | null>(null);
  const [showForm, setShowForm] = useState(false);
  const [values, setValues] = useState<FormValues>({});
  const [error, setError] = useState("");
  const [formError, setFormError] = useState("");
  const [fkOptions, setFkOptions] = useState<
    Record<string, { value: string; label: string }[]>
  >({});

  const load = useCallback(async () => {
    const params = new URLSearchParams();
    if (search) params.set("search", search);
    if (page > 1) params.set("page", String(page));
    const data = await api<ListResponse>(`${endpoint}${params.size ? `?${params}` : ""}`);
    setRows(data.results);
    setCount(data.count);
  }, [endpoint, search, page]);

  useEffect(() => {
    load().catch((err) => setError(errorMessage(err)));
  }, [load]);

  useEffect(() => {
    fields.forEach((field) => {
      if (!field.optionsEndpoint) return;
      api<ListResponse>(field.optionsEndpoint)
        .then((data) =>
          setFkOptions((prev) => ({
            ...prev,
            [field.name]: data.results.map((row) => ({
              value: String(row.id),
              label: String(row[field.optionLabelKey ?? "name"] ?? row.id),
            })),
          })),
        )
        .catch(() => undefined);
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [endpoint]);

  function initialValues(row: Row | null): FormValues {
    const result: FormValues = {};
    for (const field of fields) {
      if (field.type === "checkbox") {
        result[field.name] = row
          ? Boolean(row[field.name])
          : field.defaultValue !== undefined
            ? Boolean(field.defaultValue)
            : true;
      } else if (field.type === "password") {
        result[field.name] = "";
      } else {
        const existing = row?.[field.name];
        result[field.name] =
          existing === null || existing === undefined
            ? String(field.defaultValue ?? "")
            : String(existing);
      }
    }
    return result;
  }

  function openForm(row: Row | null) {
    setEditing(row);
    setValues(initialValues(row));
    setFormError("");
    setShowForm(true);
  }

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    const payload: Record<string, unknown> = {};
    for (const field of fields) {
      const value = values[field.name];
      if (field.type === "checkbox") {
        payload[field.name] = Boolean(value);
        continue;
      }
      if (field.type === "password" && value === "") continue;
      if (value === "" && !field.required) {
        if (field.type === "date" || field.type === "select") continue;
      }
      payload[field.name] = field.optionsEndpoint && value !== "" ? Number(value) : value;
    }
    try {
      if (editing) {
        await api(`${endpoint}${editing.id}/`, { method: "PATCH", body: payload });
      } else {
        await api(endpoint, { method: "POST", body: payload });
      }
      setShowForm(false);
      await load();
    } catch (err) {
      setFormError(errorMessage(err));
    }
  }

  async function remove(row: Row) {
    if (!window.confirm(`Delete "${formatCell(row.name ?? row.id)}"?`)) return;
    try {
      await api(`${endpoint}${row.id}/`, { method: "DELETE" });
      await load();
    } catch (err) {
      setError(errorMessage(err));
    }
  }

  function renderInput(field: FieldDef) {
    const shared =
      "w-full rounded border border-edge px-3 py-2 text-sm focus:border-primary focus:outline-none";
    const value = values[field.name];

    if (field.type === "checkbox") {
      return (
        <input
          type="checkbox"
          checked={Boolean(value)}
          onChange={(e) => setValues((prev) => ({ ...prev, [field.name]: e.target.checked }))}
        />
      );
    }
    if (field.type === "select" || field.optionsEndpoint) {
      const options = field.options ?? fkOptions[field.name] ?? [];
      return (
        <select
          className={shared}
          required={field.required}
          value={String(value ?? "")}
          onChange={(e) => setValues((prev) => ({ ...prev, [field.name]: e.target.value }))}
        >
          <option value="">— select —</option>
          {options.map((option) => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </select>
      );
    }
    if (field.type === "textarea") {
      return (
        <textarea
          className={shared}
          rows={2}
          value={String(value ?? "")}
          onChange={(e) => setValues((prev) => ({ ...prev, [field.name]: e.target.value }))}
        />
      );
    }
    return (
      <input
        className={shared}
        type={field.type ?? "text"}
        step={field.type === "number" ? "any" : undefined}
        required={field.required}
        value={String(value ?? "")}
        onChange={(e) => setValues((prev) => ({ ...prev, [field.name]: e.target.value }))}
      />
    );
  }

  return (
    <div>
      <div className="mb-4 flex flex-wrap items-center gap-3">
        <h1 className="text-xl font-semibold">{title}</h1>
        <span className="text-sm text-muted">{count} records</span>
        <div className="ml-auto flex items-center gap-2">
          <input
            className="rounded border border-edge px-3 py-1.5 text-sm"
            placeholder="Search…"
            value={search}
            onChange={(e) => {
              setSearch(e.target.value);
              setPage(1);
            }}
          />
          {canWrite && (
            <button
              className="rounded bg-primary px-3 py-1.5 text-sm font-medium text-on-primary hover:bg-primary-strong"
              onClick={() => openForm(null)}
            >
              New
            </button>
          )}
        </div>
      </div>

      {error && <p className="mb-3 text-sm text-danger">{error}</p>}

      <div className="overflow-x-auto rounded-lg border border-edge bg-surface">
        <table className="w-full text-left text-sm">
          <thead className="border-b border-edge bg-surface-2 text-xs uppercase text-muted">
            <tr>
              {columns.map((column) => (
                <th key={column.key} className="px-4 py-2.5 font-medium">
                  {column.label}
                </th>
              ))}
              {canWrite && <th className="px-4 py-2.5" />}
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr key={row.id} className="border-b border-edge-2 last:border-0">
                {columns.map((column) => (
                  <td key={column.key} className="px-4 py-2">
                    {formatCell(row[column.key])}
                  </td>
                ))}
                {canWrite && (
                  <td className="px-4 py-2 text-right whitespace-nowrap">
                    <button
                      className="text-primary hover:underline"
                      onClick={() => openForm(row)}
                    >
                      Edit
                    </button>
                    {allowDelete && (
                      <button
                        className="ml-3 text-danger hover:underline"
                        onClick={() => remove(row)}
                      >
                        Delete
                      </button>
                    )}
                  </td>
                )}
              </tr>
            ))}
            {rows.length === 0 && (
              <tr>
                <td
                  className="px-4 py-6 text-center text-faint"
                  colSpan={columns.length + 1}
                >
                  No records
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      <Pagination page={page} count={count} onPage={setPage} />

      {showForm && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
          <form
            onSubmit={submit}
            className="max-h-full w-full max-w-lg overflow-y-auto rounded-lg bg-surface p-6 shadow-xl"
          >
            <h2 className="mb-4 text-lg font-semibold">
              {editing ? `Edit ${title}` : `New ${title}`}
            </h2>
            <div className="grid gap-3">
              {fields.map((field) => (
                <label key={field.name} className="block text-sm">
                  <span className="mb-1 block font-medium text-ink-2">
                    {field.label}
                    {field.required && <span className="text-danger"> *</span>}
                  </span>
                  {renderInput(field)}
                </label>
              ))}
            </div>
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
                className="rounded bg-primary px-4 py-1.5 text-sm font-medium text-on-primary hover:bg-primary-strong"
              >
                Save
              </button>
            </div>
          </form>
        </div>
      )}
    </div>
  );
}
