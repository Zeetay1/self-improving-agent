import type { Output, Scores } from "@/lib/types";

const VARIANT_LABEL: Record<Output["variant_type"], string> = {
  headline: "Headline",
  body: "Body",
  cta: "CTA",
};

// Badge / accent color by weighted average: green >=4.0, amber 2.5-4.0, red <2.5.
function band(weighted: number) {
  if (weighted >= 4.0) {
    return { text: "text-emerald-400", border: "border-emerald-500/40", bg: "bg-emerald-500/10", bar: "bg-emerald-400/70" };
  }
  if (weighted >= 2.5) {
    return { text: "text-amber-400", border: "border-amber-500/40", bg: "bg-amber-500/10", bar: "bg-amber-400/70" };
  }
  return { text: "text-red-400", border: "border-red-500/40", bg: "bg-red-500/10", bar: "bg-red-400/70" };
}

const DIMS: { key: keyof Scores; label: string }[] = [
  { key: "hook_strength", label: "Hook" },
  { key: "brand_alignment", label: "Brand" },
  { key: "clarity", label: "Clarity" },
  { key: "conversion_intent", label: "Conv" },
];

function ScoreBar({ label, value, barClass }: { label: string; value: number; barClass: string }) {
  const pct = Math.max(0, Math.min(100, (value / 5) * 100));
  return (
    <div className="flex items-center gap-2">
      <span className="w-14 font-mono text-[10px] uppercase tracking-wider text-zinc-500">
        {label}
      </span>
      <div className="h-1.5 flex-1 bg-ink-800">
        <div className={`h-full ${barClass}`} style={{ width: `${pct}%` }} />
      </div>
      <span className="w-4 text-right font-mono text-[11px] tabular-nums text-zinc-400">
        {value}
      </span>
    </div>
  );
}

export function ResultCard({ output }: { output: Output }) {
  const { scores } = output;
  const c = band(scores.weighted_average);

  return (
    <div className="flex flex-col border border-ink-700 bg-ink-900">
      <div className="flex items-center justify-between border-b border-ink-700 px-4 py-2.5">
        <span className="font-mono text-xs uppercase tracking-wider text-zinc-400">
          {VARIANT_LABEL[output.variant_type]}
        </span>
        <span
          className={`border ${c.border} ${c.bg} ${c.text} px-2 py-0.5 font-mono text-xs tabular-nums`}
          title="Weighted average score"
        >
          {scores.weighted_average.toFixed(2)}
        </span>
      </div>

      <div className="flex-1 px-4 py-4">
        <p className="text-sm leading-relaxed text-zinc-100">{output.content}</p>
      </div>

      <div className="space-y-2 border-t border-ink-700 px-4 py-3">
        {DIMS.map((d) => (
          <ScoreBar
            key={d.key}
            label={d.label}
            value={Number(scores[d.key])}
            barClass={c.bar}
          />
        ))}
      </div>
    </div>
  );
}
