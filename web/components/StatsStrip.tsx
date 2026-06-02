import type { Stats } from "@/lib/types";

export function StatsStrip({ stats }: { stats: Stats | null }) {
  const item = (label: string, value: number | null) => (
    <span className="inline-flex items-baseline gap-1.5">
      <span className="text-zinc-500">{label}</span>
      <span className="font-mono text-zinc-200 tabular-nums">
        {value === null ? "-" : value}
      </span>
    </span>
  );

  return (
    <div className="flex items-center gap-3 border border-ink-700 bg-ink-850 px-3 py-1.5 text-xs">
      {item("Runs", stats?.runs ?? null)}
      <span className="text-ink-600">·</span>
      {item("Golden", stats?.golden ?? null)}
      <span className="text-ink-600">·</span>
      {item("Flagged", stats?.flagged ?? null)}
    </div>
  );
}
