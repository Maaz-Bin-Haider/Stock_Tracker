/**
 * Choice-list labelling and search ranking for the shared Combobox.
 *
 * Kept free of React so the ranking rules — the part that decides what a user
 * sees after typing — are unit-testable (tests/options.test.mjs), the same way
 * pagination.ts carries the paging rules.
 *
 * Why this exists: the app used native <select> elements, whose type-ahead
 * buffers keystrokes for about a second and then starts over. Typing
 * "starlink" at human speed therefore searched for "s", then "t", … and landed
 * on the first entry beginning with "k". Matching here uses the whole query,
 * matches anywhere in the label, and never expires.
 */

export interface ChoiceOption {
  value: string;
  label: string;
}

/** The shape every list endpoint returns enough of to label a row. */
export interface LabelledRow {
  id: number | string;
  name?: string | null;
  code?: string | null;
  username?: string | null;
  storage_specs?: string | null;
}

// Ranking bands, best first. Within a band the caller's original order (the
// API's, normally alphabetical) is preserved.
const EXACT = 0;
const PREFIX = 1;
const WORD_START = 2;
const SUBSTRING = 3;
const TOKENS = 4;

function normalize(text: string): string {
  return text.toLowerCase().replace(/\s+/g, " ").trim();
}

/**
 * Display label for an option row.
 *
 * Storage/specs is part of the label because two products may legitimately
 * share a name and differ only by specs (FR-018/FR-019) — without it, an
 * "iPhone 15 Pro" 256GB and 512GB are indistinguishable in a dropdown.
 */
export function optionLabel(row: LabelledRow): string {
  const base = row.name || row.code || row.username || `#${row.id}`;
  return `${base} ${row.storage_specs ?? ""}`.replace(/\s+/g, " ").trim();
}

/** Map API rows to combobox options; pass `label` for non-standard labelling. */
export function toOptions<T extends LabelledRow>(
  rows: T[],
  label: (row: T) => string = optionLabel,
): ChoiceOption[] {
  return rows.map((row) => ({ value: String(row.id), label: label(row) }));
}

function score(haystack: string, needle: string): number {
  if (haystack === needle) return EXACT;
  if (haystack.startsWith(needle)) return PREFIX;
  if (haystack.split(" ").some((word) => word.startsWith(needle))) return WORD_START;
  if (haystack.includes(needle)) return SUBSTRING;
  return TOKENS;
}

/**
 * Filter and rank options for a typed query.
 *
 * An option is kept when every whitespace-separated token appears somewhere in
 * its label, so "iphone 256" finds "iPhone 15 Pro 256GB". Ranking then puts
 * the match a typist expects first: exact, then labels starting with the
 * query, then labels with a word starting with it, then anything containing
 * it. So a lone "s" still lands on the first S entry, while the full word
 * "starlink" lands on Starlink.
 */
export function rankOptions(options: ChoiceOption[], query: string): ChoiceOption[] {
  const needle = normalize(query);
  if (!needle) return options;

  const tokens = needle.split(" ");
  const matches: { option: ChoiceOption; rank: number; index: number }[] = [];

  options.forEach((option, index) => {
    const haystack = normalize(option.label);
    if (!tokens.every((token) => haystack.includes(token))) return;
    matches.push({ option, index, rank: score(haystack, needle) });
  });

  matches.sort((a, b) => a.rank - b.rank || a.index - b.index);
  return matches.map((match) => match.option);
}

/** Index of the first option whose label starts with `letter`, or -1. */
export function firstMatchingIndex(options: ChoiceOption[], letter: string): number {
  const start = normalize(letter);
  if (!start) return -1;
  return options.findIndex((option) => normalize(option.label).startsWith(start));
}
