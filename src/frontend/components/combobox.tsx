"use client";

import { useCallback, useEffect, useId, useMemo, useRef, useState } from "react";
import { createPortal } from "react-dom";

import { firstMatchingIndex, rankOptions, type ChoiceOption } from "@/lib/options";

/**
 * Searchable single-select used for every choice control in the app.
 *
 * Replaces native <select>, whose type-ahead only buffers keystrokes for about
 * a second: typing "starlink" at normal speed searched "s", then "t", … and
 * finished on the first entry starting with "k". Here the whole query is used,
 * it matches anywhere in the label, and the list narrows as you type instead of
 * making you scroll hundreds of products.
 *
 * The list is rendered in a portal with fixed positioning so the modals'
 * `overflow-y-auto` containers cannot clip it, and it flips above the field
 * when there is no room below (SRS §7.6 — no scrolling traps on small screens).
 */

/** Above this many options the field becomes a text search box. */
const SEARCH_THRESHOLD = 8;
const MAX_LIST_HEIGHT = 288;
const GAP = 4;

interface Placement {
  left: number;
  width: number;
  top?: number;
  bottom?: number;
  maxHeight: number;
}

export default function Combobox({
  value,
  onChange,
  options,
  placeholder = "— select —",
  allowEmpty = false,
  required = false,
  disabled = false,
  className = "",
  wrapperClassName = "",
  id,
}: {
  value: string;
  onChange: (value: string) => void;
  options: ChoiceOption[];
  /** Shown when nothing is selected; also labels the clear row when allowEmpty. */
  placeholder?: string;
  /** Offer a row that clears the selection (filters, optional fields). */
  allowEmpty?: boolean;
  required?: boolean;
  disabled?: boolean;
  /** Classes for the text field itself; it is always full-width. */
  className?: string;
  /** Classes for the wrapper — set the control's width here. */
  wrapperClassName?: string;
  id?: string;
}) {
  const generatedId = useId();
  const fieldId = id ?? generatedId;
  const listId = `${fieldId}-list`;

  const inputRef = useRef<HTMLInputElement>(null);
  const fieldRef = useRef<HTMLDivElement>(null);
  const listRef = useRef<HTMLUListElement>(null);

  const [open, setOpen] = useState(false);
  /** null = showing the selection; a string = the user is typing. */
  const [query, setQuery] = useState<string | null>(null);
  const [active, setActive] = useState(0);
  const [placement, setPlacement] = useState<Placement | null>(null);

  const selected = useMemo(
    () => options.find((option) => option.value === value) ?? null,
    [options, value],
  );

  // Short lists stay read-only so a tablet keyboard does not open for a
  // two-choice field; a required field must stay editable, because read-only
  // controls are barred from the browser's own "please fill this in" check.
  const searchable = options.length > SEARCH_THRESHOLD || required;

  const rows = useMemo(() => {
    const matched = query ? rankOptions(options, query) : options;
    // The clear row belongs to the unfiltered list only — while searching, the
    // user is looking for a value, not for "All".
    return allowEmpty && !query ? [{ value: "", label: placeholder }, ...matched] : matched;
  }, [options, query, allowEmpty, placeholder]);

  const reposition = useCallback(() => {
    const field = fieldRef.current;
    if (!field) return;
    const box = field.getBoundingClientRect();
    const below = window.innerHeight - box.bottom - GAP * 2;
    const above = box.top - GAP * 2;
    const flip = below < Math.min(MAX_LIST_HEIGHT, above);
    setPlacement({
      left: box.left,
      width: box.width,
      top: flip ? undefined : box.bottom + GAP,
      bottom: flip ? window.innerHeight - box.top + GAP : undefined,
      maxHeight: Math.max(120, Math.min(MAX_LIST_HEIGHT, flip ? above : below)),
    });
  }, []);

  const openList = useCallback(() => {
    if (disabled) return;
    reposition();
    setOpen(true);
  }, [disabled, reposition]);

  /** Close the list. Committing resolves a fully typed label to its option. */
  const close = useCallback(
    (commit: boolean) => {
      if (commit && query) {
        const typed = query.trim().toLowerCase();
        const exact = options.find((option) => option.label.toLowerCase() === typed);
        if (exact) onChange(exact.value);
      }
      setQuery(null);
      setOpen(false);
    },
    [query, options, onChange],
  );

  function choose(option: ChoiceOption) {
    onChange(option.value);
    setQuery(null);
    setOpen(false);
    inputRef.current?.focus();
  }

  // Keep the list glued to the field while a modal or the page scrolls.
  useEffect(() => {
    if (!open) return undefined;
    const handle = () => reposition();
    window.addEventListener("scroll", handle, true);
    window.addEventListener("resize", handle);
    return () => {
      window.removeEventListener("scroll", handle, true);
      window.removeEventListener("resize", handle);
    };
  }, [open, reposition]);

  // Focus leaving the field closes it, but a click on a non-focusable part of
  // the page does not always move focus (Safari especially), so watch pointers
  // too — otherwise a list could be left hanging open over the page.
  useEffect(() => {
    if (!open) return undefined;
    const onPointerDown = (event: Event) => {
      const target = event.target as Node;
      if (fieldRef.current?.contains(target) || listRef.current?.contains(target)) return;
      close(true);
    };
    document.addEventListener("pointerdown", onPointerDown, true);
    return () => document.removeEventListener("pointerdown", onPointerDown, true);
  }, [open, close]);

  useEffect(() => {
    if (!open) return;
    const index = rows.findIndex((row) => row.value === value);
    setActive(query ? 0 : Math.max(index, 0));
    // Only when the list opens or the query changes — not on every rows identity.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open, query]);

  useEffect(() => {
    if (!open) return;
    listRef.current?.querySelector(`[data-index="${active}"]`)?.scrollIntoView({ block: "nearest" });
  }, [active, open]);

  function move(delta: number) {
    if (rows.length === 0) return;
    setActive((current) => Math.min(rows.length - 1, Math.max(0, current + delta)));
  }

  function handleKeyDown(event: React.KeyboardEvent<HTMLInputElement>) {
    if (disabled) return;
    switch (event.key) {
      case "ArrowDown":
      case "ArrowUp":
        event.preventDefault();
        if (!open) openList();
        else move(event.key === "ArrowDown" ? 1 : -1);
        return;
      case "Home":
      case "End":
        if (!open) return;
        event.preventDefault();
        setActive(event.key === "Home" ? 0 : rows.length - 1);
        return;
      case "Enter":
        if (!open) return;
        event.preventDefault();
        if (rows[active]) choose(rows[active]);
        return;
      case "Escape":
        if (!open) return;
        // Stop here so a surrounding dialog does not also close.
        event.preventDefault();
        event.stopPropagation();
        close(false);
        return;
      case "Tab":
        close(true);
        return;
      default:
        break;
    }
    // Read-only short lists keep the native <select> convenience of jumping to
    // an entry by its first letter — without the timeout that caused the bug.
    if (!searchable && event.key.length === 1) {
      event.preventDefault();
      if (!open) openList();
      const index = firstMatchingIndex(rows, event.key);
      if (index >= 0) setActive(index);
    }
  }

  return (
    <div
      ref={fieldRef}
      className={`relative ${wrapperClassName}`}
      onBlur={(event) => {
        if (fieldRef.current?.contains(event.relatedTarget as Node | null)) return;
        close(true);
      }}
    >
      <input
        ref={inputRef}
        id={fieldId}
        type="text"
        role="combobox"
        aria-expanded={open}
        aria-controls={open ? listId : undefined}
        aria-activedescendant={open && rows[active] ? `${listId}-${active}` : undefined}
        aria-autocomplete={searchable ? "list" : "none"}
        autoComplete="off"
        className={`w-full ${className} pr-14 text-left`}
        placeholder={placeholder}
        required={required}
        disabled={disabled}
        readOnly={!searchable}
        value={query ?? selected?.label ?? ""}
        onChange={(event) => {
          setQuery(event.target.value);
          if (!open) openList();
        }}
        onClick={() => (open ? undefined : openList())}
        onKeyDown={handleKeyDown}
      />

      <div className="pointer-events-none absolute inset-y-0 right-0 flex items-center gap-0.5 pr-1.5">
        {allowEmpty && value !== "" && !disabled && (
          <button
            type="button"
            tabIndex={-1}
            aria-label="Clear selection"
            className="pointer-events-auto rounded px-1 text-muted hover:text-ink"
            onClick={() => {
              onChange("");
              setQuery(null);
              inputRef.current?.focus();
            }}
          >
            ×
          </button>
        )}
        <button
          type="button"
          tabIndex={-1}
          aria-label={open ? "Close list" : "Open list"}
          disabled={disabled}
          className="pointer-events-auto rounded px-1 text-muted hover:text-ink disabled:opacity-50"
          onClick={() => {
            if (open) close(true);
            else openList();
            inputRef.current?.focus();
          }}
        >
          <svg
            width={12}
            height={12}
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth={2.4}
            strokeLinecap="round"
            strokeLinejoin="round"
            aria-hidden="true"
            className={open ? "rotate-180 transition-transform" : "transition-transform"}
          >
            <path d="m6 9 6 6 6-6" />
          </svg>
        </button>
      </div>

      {open &&
        placement &&
        createPortal(
          <ul
            ref={listRef}
            id={listId}
            role="listbox"
            // Focus must stay in the input, or the field would blur and close
            // before the click lands on an option.
            onMouseDown={(event) => event.preventDefault()}
            style={{
              position: "fixed",
              left: placement.left,
              width: placement.width,
              top: placement.top,
              bottom: placement.bottom,
              maxHeight: placement.maxHeight,
            }}
            className="z-[60] overflow-y-auto overscroll-contain rounded-md border border-edge bg-surface py-1 text-sm shadow-lg"
          >
            {rows.length === 0 && (
              <li className="px-3 py-2 text-muted">No match for “{query}”.</li>
            )}
            {rows.map((row, index) => {
              const isSelected = row.value === value;
              return (
                <li
                  key={`${row.value}-${index}`}
                  id={`${listId}-${index}`}
                  data-index={index}
                  role="option"
                  aria-selected={isSelected}
                  onMouseEnter={() => setActive(index)}
                  onClick={() => choose(row)}
                  className={`cursor-pointer px-3 py-2 ${
                    index === active ? "bg-primary-soft text-ink" : "text-ink"
                  } ${isSelected ? "font-medium" : ""} ${row.value === "" ? "text-muted" : ""}`}
                >
                  {row.label}
                </li>
              );
            })}
          </ul>,
          document.body,
        )}
    </div>
  );
}
