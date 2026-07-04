"use client";

import { useEffect, useState } from "react";

export default function Home() {
  const [apiStatus, setApiStatus] = useState("checking…");

  useEffect(() => {
    fetch("/api/v1/health/")
      .then((res) => res.json())
      .then((data: { status: string }) => setApiStatus(data.status))
      .catch(() => setApiStatus("unreachable"));
  }, []);

  return (
    <main className="flex min-h-screen flex-col items-center justify-center gap-4">
      <h1 className="text-3xl font-semibold">SwissTech Stock Tracker</h1>
      <p className="text-sm text-slate-500">
        Backend API health: <span className="font-mono">{apiStatus}</span>
      </p>
    </main>
  );
}
