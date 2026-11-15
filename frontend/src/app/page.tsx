"use client";

import { useEffect, useState } from "react";

type Health = { status: string; database: string };

export default function Home() {
  const [health, setHealth] = useState<Health | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetch("/api/health")
      .then((res) => res.json())
      .then(setHealth)
      .catch((err) => setError(String(err)));
  }, []);

  return (
    <main style={{ padding: "2rem", fontFamily: "system-ui, sans-serif" }}>
      <h1>TeamSpend</h1>
      <p>Backend status:</p>
      <pre>{health ? JSON.stringify(health, null, 2) : (error ?? "Loading...")}</pre>
    </main>
  );
}
