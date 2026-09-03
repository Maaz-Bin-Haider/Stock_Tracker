"use client";

import { useEffect, useState } from "react";

import {
  ICON_PATHS,
  currentWorkspace,
  otherWorkspaces,
  type Workspace,
  type WorkspaceIcon,
} from "@/lib/workspaces";

/** Matches the CSS keyframe timeline in app/globals.css. */
const FULL_DURATION = 1050;
const REDUCED_DURATION = 320;

function accentStyle(workspace: Workspace): React.CSSProperties {
  return {
    ["--ws-accent" as never]: `var(--ws-${workspace.accent})`,
    ["--ws-accent-soft" as never]: `var(--ws-${workspace.accent}-soft)`,
  };
}

function Glyph({ icon, size }: { icon: WorkspaceIcon; size: number }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={1.7}
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      {ICON_PATHS[icon].map((d) => (
        <path key={d} d={d} />
      ))}
    </svg>
  );
}

/**
 * Sidebar control for moving to another system.
 *
 * With one other workspace the button goes straight there; once a third system
 * is added to lib/workspaces.ts, hovering (or focusing) opens the list to
 * choose from. Every option is a real link, so it still works if the
 * animation never runs.
 */
export default function WorkspaceSwitcher() {
  const from = currentWorkspace();
  const others = otherWorkspaces();
  const [open, setOpen] = useState(false);
  const [leavingTo, setLeavingTo] = useState<Workspace | null>(null);

  useEffect(() => {
    if (!leavingTo) return undefined;
    const reduced =
      typeof window.matchMedia === "function" &&
      window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    const timer = window.setTimeout(
      () => {
        window.location.href = leavingTo.url;
      },
      reduced ? REDUCED_DURATION : FULL_DURATION,
    );
    return () => window.clearTimeout(timer);
  }, [leavingTo]);

  if (others.length === 0) return null;

  function leave(target: Workspace, event: React.MouseEvent) {
    // Leave modified clicks alone so "open in new tab" still behaves.
    if (event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
    event.preventDefault();
    if (leavingTo) return;
    setLeavingTo(target);
  }

  const single = others.length === 1 ? others[0] : null;

  const triggerContent = (
    <>
      <svg
        width={14}
        height={14}
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth={1.9}
        strokeLinecap="round"
        strokeLinejoin="round"
        aria-hidden="true"
      >
        <path d="M8 3 4 7l4 4" />
        <path d="M4 7h16" />
        <path d="m16 21 4-4-4-4" />
        <path d="M20 17H4" />
      </svg>
      <span className="flex-1 text-left">Switch workspace</span>
      <svg
        width={11}
        height={11}
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth={2.4}
        strokeLinecap="round"
        strokeLinejoin="round"
        aria-hidden="true"
        className={`opacity-50 transition-transform duration-200 ${open ? "rotate-180" : ""}`}
      >
        <path d="m6 9 6 6 6-6" />
      </svg>
    </>
  );

  const triggerClass =
    "flex w-full items-center gap-2.5 rounded-md px-3 py-[0.58rem] text-[0.875rem] text-sidebar-link transition-colors hover:bg-[rgba(255,255,255,0.06)] hover:text-white";

  return (
    <div
      className="border-b border-sidebar-border px-3 py-2.5"
      onMouseEnter={() => setOpen(true)}
      onMouseLeave={() => setOpen(false)}
      onFocus={() => setOpen(true)}
    >
      {single ? (
        <a href={single.url} onClick={(event) => leave(single, event)} className={triggerClass}>
          {triggerContent}
        </a>
      ) : (
        <button
          type="button"
          aria-expanded={open}
          onClick={() => setOpen((value) => !value)}
          className={triggerClass}
        >
          {triggerContent}
        </button>
      )}

      <div
        className={`overflow-hidden transition-all duration-300 ${
          open ? "max-h-80 opacity-100" : "max-h-0 opacity-0"
        }`}
      >
        {others.map((workspace) => (
          <a
            key={workspace.id}
            href={workspace.url}
            onClick={(event) => leave(workspace, event)}
            style={accentStyle(workspace)}
            className="mt-1 flex items-center gap-2 rounded-md px-2 py-1.5 transition-colors hover:bg-[rgba(255,255,255,0.06)]"
          >
            <span
              className="flex h-7 w-7 shrink-0 items-center justify-center rounded-lg"
              style={{ color: "var(--ws-accent)", background: "var(--ws-accent-soft)" }}
            >
              <Glyph icon={workspace.icon} size={14} />
            </span>
            <span className="min-w-0">
              <span className="block text-[0.8rem] font-medium text-sidebar-text">{workspace.name}</span>
              <span className="block truncate text-[0.66rem] text-sidebar-link opacity-70">
                {workspace.modules.join(" · ")}
              </span>
            </span>
          </a>
        ))}
      </div>

      {leavingTo && (
        <div className="ws-transition" role="status" aria-live="polite">
          <div className="ws-transition-card">
            <div className="ws-transition-marks">
              <span className="ws-transition-mark is-from" style={accentStyle(from)}>
                <Glyph icon={from.icon} size={24} />
              </span>
              <span className="ws-transition-track" style={accentStyle(leavingTo)}>
                <span className="ws-transition-pulse" />
              </span>
              <span className="ws-transition-mark is-to" style={accentStyle(leavingTo)}>
                <Glyph icon={leavingTo.icon} size={24} />
              </span>
            </div>
            <div className="ws-transition-text">
              <p className="text-base font-semibold text-ink">Opening {leavingTo.name}</p>
              <p className="mt-1 text-xs text-muted">
                {leavingTo.signsIn ? "Signing you in…" : "Taking you there…"}
              </p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
