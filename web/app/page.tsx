"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { BriefForm } from "@/components/BriefForm";
import { HowItWorks } from "@/components/HowItWorks";
import { ResultCard } from "@/components/ResultCard";
import { StatsStrip } from "@/components/StatsStrip";
import { ApiError, getStats, runAgent } from "@/lib/api";
import type { Brief, RunResponse, Stats } from "@/lib/types";

const EXAMPLE_BRIEF: Brief = {
  brand: "FitFuel",
  product: "High-protein meal replacement shake",
  audience: "Busy professionals aged 25-40",
  tone: "Energetic and no-nonsense",
  goal: "Drive trial purchases",
};

// Ordered variant rendering regardless of backend ordering.
const ORDER: RunResponse["outputs"][number]["variant_type"][] = [
  "headline",
  "body",
  "cta",
];

const LOADING_PHASES = [
  "Retrieving examples…",
  "Generating variants…",
  "Scoring with the judge…",
];

export default function Page() {
  const [brief, setBrief] = useState<Brief>(EXAMPLE_BRIEF);
  const [loading, setLoading] = useState(false);
  const [phase, setPhase] = useState(0);
  const [result, setResult] = useState<RunResponse | null>(null);
  const [stats, setStats] = useState<Stats | null>(null);
  const [error, setError] = useState<string | null>(null);
  const phaseTimer = useRef<ReturnType<typeof setInterval> | null>(null);

  const refreshStats = useCallback(async () => {
    try {
      setStats(await getStats());
    } catch {
      // Stats are non-critical; leave them dashed if unreachable.
    }
  }, []);

  useEffect(() => {
    refreshStats();
  }, [refreshStats]);

  // Advance the loading status text while a run is in flight.
  useEffect(() => {
    if (loading) {
      setPhase(0);
      phaseTimer.current = setInterval(() => {
        setPhase((p) => Math.min(p + 1, LOADING_PHASES.length - 1));
      }, 1100);
    } else if (phaseTimer.current) {
      clearInterval(phaseTimer.current);
      phaseTimer.current = null;
    }
    return () => {
      if (phaseTimer.current) clearInterval(phaseTimer.current);
    };
  }, [loading]);

  const onChange = (key: keyof Brief, value: string) =>
    setBrief((b) => ({ ...b, [key]: value }));

  const onSubmit = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await runAgent(brief);
      setResult(data);
      await refreshStats();
    } catch (e) {
      const msg = e instanceof ApiError ? e.message : "Something went wrong.";
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  const orderedOutputs = result
    ? ORDER.map((t) => result.outputs.find((o) => o.variant_type === t)).filter(
        (o): o is RunResponse["outputs"][number] => Boolean(o),
      )
    : [];

  return (
    <main className="mx-auto max-w-5xl px-5 py-10 sm:py-14">
      {/* Header */}
      <header className="mb-10 flex flex-col gap-4 border-b border-ink-700 pb-6 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <h1 className="text-xl font-semibold tracking-tight text-zinc-50 sm:text-2xl">
            Self-Improving Ad Copy Agent
          </h1>
          <p className="mt-1.5 max-w-xl text-sm leading-relaxed text-zinc-500">
            Generates DTC ad copy, scores its own output with an LLM judge,
            remembers the winners, and gets better with every run.
          </p>
        </div>
        <div className="sm:pt-1">
          <StatsStrip stats={stats} />
        </div>
      </header>

      {/* Brief form */}
      <BriefForm
        brief={brief}
        onChange={onChange}
        onSubmit={onSubmit}
        loading={loading}
        statusText={LOADING_PHASES[phase]}
      />

      {/* Error */}
      {error && (
        <div className="mt-5 border border-red-500/40 bg-red-500/10 px-4 py-3 text-sm text-red-300">
          {error}
        </div>
      )}

      {/* Results */}
      {result && (
        <section className="mt-8">
          {result.retrieved_count > 0 && (
            <p className="mb-3 font-mono text-xs text-zinc-500">
              <span className="text-emerald-400">↺</span> Informed by{" "}
              {result.retrieved_count} past high-scoring example
              {result.retrieved_count === 1 ? "" : "s"}.
            </p>
          )}
          <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
            {orderedOutputs.map((o) => (
              <ResultCard key={o.variant_type} output={o} />
            ))}
          </div>
          <p className="mt-3 font-mono text-[11px] text-zinc-600">
            run #{result.run_id} · prompt {result.prompt_version}
            {result.feedback.promoted_to_golden.length > 0 &&
              ` · promoted: ${result.feedback.promoted_to_golden.join(", ")}`}
          </p>
        </section>
      )}

      {/* How it works */}
      <div className="mt-12">
        <HowItWorks />
      </div>

      <footer className="mt-10 border-t border-ink-700 pt-5 font-mono text-[11px] text-zinc-600">
        Backend: FastAPI on Railway · Frontend: Next.js on Vercel · Judge &
        generator: llama-3.3-70b
      </footer>
    </main>
  );
}
