"use client";

import { useCallback, useEffect, useRef, useState } from "react";

import { api, apiUpload, errorMessage } from "@/lib/api";

interface Attachment {
  id: number;
  original_name: string;
  content_type: string;
  size: number;
  uploaded_by_username: string;
  uploaded_at: string;
  download_url: string;
}

/**
 * Invoice/bill files on a purchase or sale (FR-035/FR-073): list, download,
 * upload (images + PDF), delete. The server enforces module-level write roles.
 */
export default function AttachmentsPanel({
  module,
  recordId,
  canWrite,
}: {
  module: "purchases" | "sales";
  recordId: number;
  canWrite: boolean;
}) {
  const [files, setFiles] = useState<Attachment[]>([]);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const fileInput = useRef<HTMLInputElement | null>(null);

  const load = useCallback(async () => {
    const data = await api<{ results: Attachment[] }>(
      `/api/v1/attachments/?module=${module}&record_id=${recordId}`,
    );
    setFiles(data.results);
  }, [module, recordId]);

  useEffect(() => {
    load().catch((err) => setError(errorMessage(err)));
  }, [load]);

  async function upload(file: File) {
    setBusy(true);
    setError("");
    const form = new FormData();
    form.set("module", module);
    form.set("record_id", String(recordId));
    form.set("file", file);
    try {
      await apiUpload("/api/v1/attachments/", form);
      await load();
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setBusy(false);
      if (fileInput.current) fileInput.current.value = "";
    }
  }

  async function remove(attachment: Attachment) {
    if (!window.confirm(`Delete "${attachment.original_name}"?`)) return;
    try {
      await api(`/api/v1/attachments/${attachment.id}/`, { method: "DELETE" });
      await load();
    } catch (err) {
      setError(errorMessage(err));
    }
  }

  return (
    <div className="mt-3 rounded border border-edge bg-surface p-3">
      <div className="mb-2 flex items-center gap-3">
        <span className="text-xs font-semibold uppercase text-muted">
          Invoice files ({files.length})
        </span>
        {canWrite && (
          <>
            <input
              ref={fileInput}
              type="file"
              accept=".pdf,.png,.jpg,.jpeg,.webp,application/pdf,image/*"
              className="hidden"
              onChange={(e) => {
                const file = e.target.files?.[0];
                if (file) upload(file);
              }}
            />
            <button
              className="rounded border border-edge px-2 py-1 text-xs text-ink-2 hover:bg-surface-2 disabled:opacity-50"
              disabled={busy}
              onClick={() => fileInput.current?.click()}
            >
              {busy ? "Uploading…" : "Upload file"}
            </button>
            <span className="text-xs text-faint">PDF or image, max 10 MB</span>
          </>
        )}
      </div>
      {error && <p className="mb-2 text-xs text-danger">{error}</p>}
      {files.length === 0 ? (
        <p className="text-xs text-faint">No files uploaded.</p>
      ) : (
        <ul className="space-y-1 text-sm">
          {files.map((attachment) => (
            <li key={attachment.id} className="flex flex-wrap items-center gap-2">
              <a href={attachment.download_url} className="text-primary hover:underline">
                {attachment.original_name}
              </a>
              <span className="text-xs text-faint">
                {(attachment.size / 1024).toFixed(0)} KB · {attachment.uploaded_by_username}
              </span>
              {canWrite && (
                <button
                  className="text-xs text-danger hover:underline"
                  onClick={() => remove(attachment)}
                >
                  Delete
                </button>
              )}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
