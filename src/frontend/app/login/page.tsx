"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { api, errorMessage } from "@/lib/api";

export default function LoginPage() {
  const router = useRouter();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      await api("/api/v1/auth/login/", { method: "POST", body: { username, password } });
      router.replace("/");
    } catch (err) {
      setError(errorMessage(err));
      setBusy(false);
    }
  }

  return (
    <main className="flex min-h-screen items-center justify-center p-4">
      <form
        onSubmit={submit}
        className="w-full max-w-sm rounded-lg border border-edge bg-surface p-8 shadow-sm"
      >
        <h1 className="mb-1 text-xl font-semibold">SwissTech Stock Tracker</h1>
        <p className="mb-6 text-sm text-muted">Sign in to continue</p>

        <label className="mb-3 block text-sm">
          <span className="mb-1 block font-medium text-ink-2">Username</span>
          <input
            className="w-full rounded border border-edge px-3 py-2 text-sm focus:border-primary focus:outline-none"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            autoFocus
            required
          />
        </label>
        <label className="mb-4 block text-sm">
          <span className="mb-1 block font-medium text-ink-2">Password</span>
          <input
            type="password"
            className="w-full rounded border border-edge px-3 py-2 text-sm focus:border-primary focus:outline-none"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
          />
        </label>

        {error && <p className="mb-4 text-sm text-danger">{error}</p>}

        <button
          type="submit"
          disabled={busy}
          className="w-full rounded bg-primary py-2 text-sm font-medium text-on-primary hover:bg-primary-strong disabled:opacity-50"
        >
          {busy ? "Signing in…" : "Sign in"}
        </button>
      </form>
    </main>
  );
}
