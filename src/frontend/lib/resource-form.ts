/**
 * Payload building for the generic master-data form (components/resource-crud).
 *
 * Kept out of the component so the rules are unit-testable, the same way
 * pagination.ts and options.ts are.
 *
 * The rule that matters: edits save with PATCH, where an omitted key means
 * "leave this alone". A field the user has cleared must therefore be sent as
 * an explicit null, or clearing it silently does nothing — which is how a GST
 * rate ended up with an end date nobody could remove.
 */

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

export type FormValues = Record<string, string | boolean>;

/** Fields whose emptiness means "no value", rather than the empty string. */
function isNullable(field: FieldDef): boolean {
  return field.type === "date" || field.type === "select" || Boolean(field.optionsEndpoint);
}

export function buildPayload(
  fields: FieldDef[],
  values: FormValues,
): Record<string, unknown> {
  const payload: Record<string, unknown> = {};

  for (const field of fields) {
    const value = values[field.name];

    if (field.type === "checkbox") {
      payload[field.name] = Boolean(value);
      continue;
    }
    // A blank password means "keep the current one" — the one case where
    // leaving a field out is the intended meaning.
    if (field.type === "password" && value === "") continue;

    if (value === "" && !field.required && isNullable(field)) {
      payload[field.name] = null;
      continue;
    }

    // Foreign keys arrive as strings from the form and must go back as ids;
    // static choices (roles, enums) are already the value the API expects.
    payload[field.name] =
      field.optionsEndpoint && value !== "" ? Number(value) : value;
  }

  return payload;
}
