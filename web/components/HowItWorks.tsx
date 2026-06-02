const STEPS = [
  {
    n: "01",
    title: "Generate",
    body: "The agent turns a brand brief into three ad-copy variants: a headline hook, body copy, and a CTA.",
  },
  {
    n: "02",
    title: "Judge",
    body: "A separate LLM-as-judge scores each variant 1–5 on four dimensions: hook strength, brand alignment, clarity, and conversion intent.",
  },
  {
    n: "03",
    title: "Remember",
    body: "Outputs scoring ≥ 4.0 are promoted into a golden dataset and a vector memory; weak ones (< 2.5) get flagged for review.",
  },
  {
    n: "04",
    title: "Improve & guard",
    body: "Future runs retrieve those winners as few-shot examples, so quality compounds, and a regression gate blocks any prompt change that drops golden scores.",
  },
];

export function HowItWorks() {
  return (
    <section className="border border-ink-700 bg-ink-900">
      <div className="border-b border-ink-700 px-5 py-3">
        <h2 className="font-mono text-xs uppercase tracking-wider text-zinc-400">
          How it works
        </h2>
      </div>
      <div className="grid grid-cols-1 gap-px bg-ink-700 sm:grid-cols-2 lg:grid-cols-4">
        {STEPS.map((s) => (
          <div key={s.n} className="bg-ink-900 px-5 py-5">
            <div className="mb-2 flex items-center gap-2">
              <span className="font-mono text-xs text-zinc-600">{s.n}</span>
              <span className="text-sm font-medium text-zinc-200">{s.title}</span>
            </div>
            <p className="text-[13px] leading-relaxed text-zinc-500">{s.body}</p>
          </div>
        ))}
      </div>
    </section>
  );
}
