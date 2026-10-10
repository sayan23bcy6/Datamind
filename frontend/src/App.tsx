import { useEffect, useState } from "react";

const API_BASE_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

export default function App() {
  const [status, setStatus] = useState("Checking backend...");
  const [health, setHealth] = useState<{
    status?: string;
    service?: string;
    environment?: string;
  } | null>(null);

  useEffect(() => {
    fetch(`${API_BASE_URL}/api/v1/health`)
      .then(async (response) => {
        const payload = await response.json();
        setHealth(payload);
        setStatus(response.ok ? "Backend ready" : "Backend unreachable");
      })
      .catch(() => {
        setStatus("Backend unreachable");
        setHealth(null);
      });
  }, []);

  return (
    <main className="min-h-screen bg-slate-950 text-slate-100">
      <div className="mx-auto flex max-w-6xl flex-col px-6 py-16">
        <header className="mb-12 flex items-center justify-between gap-4">
          <div>
            <p className="text-sm font-semibold uppercase tracking-[0.2em] text-cyan-300">
              Autonomous data quality
            </p>
            <h1 className="mt-3 text-4xl font-black tracking-tight sm:text-5xl">
              DataMind
            </h1>
          </div>
          <button className="rounded-full border border-cyan-400/40 bg-cyan-400/10 px-5 py-2.5 text-sm font-medium text-cyan-200 transition hover:bg-cyan-400/20">
            Try the demo dataset
          </button>
        </header>

        <section className="grid gap-8 lg:grid-cols-[1.4fr_0.6fr] lg:items-center">
          <div>
            <p className="inline-flex rounded-full border border-violet-400/40 bg-violet-500/10 px-3 py-1 text-xs font-semibold uppercase tracking-[0.18em] text-violet-200">
              LLM reasoning + deterministic checks
            </p>
            <h2 className="mt-6 max-w-xl text-5xl font-black leading-tight tracking-tight text-white">
              Detect issues. Explain them. Verify the fix.
            </h2>
            <p className="mt-5 max-w-xl text-lg text-slate-300">
              DataMind profiles messy CSV and spreadsheet data, surfaces quality
              risks, and runs an investigation loop that explains every repair
              with evidence.
            </p>
            <div className="mt-8 flex flex-wrap gap-4">
              <button className="rounded-xl bg-gradient-to-r from-violet-500 to-cyan-500 px-5 py-3 font-semibold text-white shadow-xl shadow-violet-900/20 transition hover:scale-[1.01]">
                Start investigation
              </button>
              <button className="rounded-xl border border-slate-700 bg-slate-900/70 px-5 py-3 font-semibold text-slate-200">
                View pipeline
              </button>
            </div>
          </div>

          <div className="rounded-2xl border border-slate-800 bg-slate-900/70 p-6 shadow-2xl shadow-slate-950/50 backdrop-blur">
            <div className="mb-5 flex items-center justify-between">
              <span className="text-sm font-medium text-slate-300">
                Pipeline status
              </span>
              <span className="rounded-full border border-emerald-500/40 bg-emerald-500/10 px-2 py-1 text-xs font-semibold text-emerald-300">
                {status}
              </span>
            </div>

            <div className="space-y-4">
              {[
                ["Profile data", "Ready"],
                ["Investigate issues", "Queued"],
                ["Critic review", "Queued"],
                ["Verify repairs", "Queued"],
              ].map(([label, value]) => (
                <div
                  key={label}
                  className="rounded-xl border border-slate-800 bg-slate-950/60 p-3"
                >
                  <div className="flex items-center justify-between text-sm text-slate-300">
                    <span>{label}</span>
                    <span className="font-medium text-slate-100">{value}</span>
                  </div>
                </div>
              ))}
            </div>

            {health ? (
              <div className="mt-6 rounded-xl border border-cyan-500/20 bg-cyan-500/5 p-3 text-sm text-cyan-100">
                <div>service: {health.service}</div>
                <div>environment: {health.environment}</div>
                <div>status: {health.status}</div>
              </div>
            ) : null}
          </div>
        </section>
      </div>
    </main>
  );
}
