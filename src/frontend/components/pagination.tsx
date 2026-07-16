"use client";

/** Prev/Next pager for DRF page-number pagination (PAGE_SIZE = 50). */
export default function Pagination({
  page,
  count,
  onPage,
  pageSize = 50,
}: {
  page: number;
  count: number;
  onPage: (page: number) => void;
  pageSize?: number;
}) {
  const pages = Math.max(1, Math.ceil(count / pageSize));
  if (pages <= 1) return null;

  const buttonClass =
    "rounded border border-edge bg-surface px-3 py-1 text-sm text-ink-2 hover:bg-surface-2 disabled:opacity-40";
  return (
    <div className="mt-3 flex items-center gap-3 text-sm text-muted">
      <button className={buttonClass} disabled={page <= 1} onClick={() => onPage(page - 1)}>
        ← Prev
      </button>
      <span>
        Page {page} of {pages}
      </span>
      <button
        className={buttonClass}
        disabled={page >= pages}
        onClick={() => onPage(page + 1)}
      >
        Next →
      </button>
    </div>
  );
}
