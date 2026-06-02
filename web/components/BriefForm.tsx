import type { Brief } from "@/lib/types";

const FIELDS: { key: keyof Brief; label: string; placeholder: string }[] = [
  { key: "brand", label: "Brand", placeholder: "FitFuel" },
  { key: "product", label: "Product", placeholder: "High-protein meal replacement shake" },
  { key: "audience", label: "Audience", placeholder: "Busy professionals aged 25-40" },
  { key: "tone", label: "Tone", placeholder: "Energetic and no-nonsense" },
  { key: "goal", label: "Goal", placeholder: "Drive trial purchases" },
];

export function BriefForm({
  brief,
  onChange,
  onSubmit,
  loading,
  statusText,
}: {
  brief: Brief;
  onChange: (key: keyof Brief, value: string) => void;
  onSubmit: () => void;
  loading: boolean;
  statusText: string;
}) {
  return (
    <form
      onSubmit={(e) => {
        e.preventDefault();
        onSubmit();
      }}
      className="border border-ink-700 bg-ink-900"
    >
      <div className="border-b border-ink-700 px-5 py-3">
        <h2 className="font-mono text-xs uppercase tracking-wider text-zinc-400">
          Brand Brief
        </h2>
      </div>

      <div className="grid grid-cols-1 gap-4 px-5 py-5 sm:grid-cols-2">
        {FIELDS.map((f) => (
          <div
            key={f.key}
            className={f.key === "product" ? "sm:col-span-2" : undefined}
          >
            <label
              htmlFor={f.key}
              className="mb-1.5 block font-mono text-[11px] uppercase tracking-wider text-zinc-500"
            >
              {f.label}
            </label>
            <input
              id={f.key}
              type="text"
              value={brief[f.key]}
              placeholder={f.placeholder}
              onChange={(e) => onChange(f.key, e.target.value)}
              disabled={loading}
              className="w-full border border-ink-700 bg-ink-950 px-3 py-2 text-sm text-zinc-100 outline-none transition-colors placeholder:text-zinc-600 focus:border-zinc-500 disabled:opacity-60"
            />
          </div>
        ))}
      </div>

      <div className="flex items-center justify-between gap-4 border-t border-ink-700 px-5 py-4">
        <p
          className={`font-mono text-xs text-zinc-500 ${
            loading ? "animate-soft-pulse" : ""
          }`}
        >
          {loading ? statusText : "Ready"}
        </p>
        <button
          type="submit"
          disabled={loading}
          className="border border-zinc-300 bg-zinc-100 px-4 py-2 text-sm font-medium text-ink-950 transition-colors hover:bg-white disabled:cursor-not-allowed disabled:border-ink-600 disabled:bg-ink-700 disabled:text-zinc-400"
        >
          {loading ? "Running..." : "Generate Copy"}
        </button>
      </div>
    </form>
  );
}
