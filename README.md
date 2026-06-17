---
title: Self Improving Ad Copy Agent
emoji: 🧠
colorFrom: gray
colorTo: gray
sdk: docker
pinned: false
---

# Self-Improving Ad Copy Agent

A small agentic system that generates direct-to-consumer (DTC) ad copy,
evaluates its **own** outputs with an LLM-as-judge, stores the results, and
uses that signal to improve over time. The loop runs end to end:

```
retrieve -> generate -> evaluate -> log -> improve -> repeat
```

Every good output becomes future few-shot fuel and a regression baseline; every
bad output gets flagged for review. The system gets better the more it runs,
without any human editing prompts in the hot path.

---

## Live Demo

**🔗 Live demo:** https://adcopy.zeetay.dev

The hosted demo runs the full loop from the browser: fill the brief (pre-filled
with a FitFuel example), click **Generate**, and watch the agent retrieve past
winners, generate three variants, and score each on four dimensions in real time.

- **Frontend:** Next.js (App Router) deployed on **Netlify**, in [`web/`](web/).
- **Backend:** the FastAPI app deployed on **Hugging Face Spaces** (Docker, see [`Dockerfile`](Dockerfile)),
  with CORS, a per-IP rate limit on `/run`, a `/stats` endpoint, and a startup
  seed so a fresh deployment shows non-zero stats and working retrieval on the
  very first visit.

> Deployment env vars: the backend needs `GROQ_API_KEY` (and optionally
> `CORS_ORIGINS` = your site URL); the frontend needs `NEXT_PUBLIC_API_URL` =
> your Hugging Face Space URL. See the per-app `.env.example` files.

---

## What it does (and why it's architecturally interesting)

Most "LLM app" demos are a single prompt with no memory and no notion of
quality. This project is built around three ideas that make it a genuine
*self-improving* loop:

1. **It judges itself on multiple axes.** Each output is scored 1-5 on four
   independent dimensions (hook strength, brand alignment, clarity, conversion
   intent) by a separate judge model. Dimension scores are first-class and
   stored separately; there is no single "vibe" score driving decisions.

2. **It remembers what worked.** High-scoring outputs are embedded by their
   brand brief and stored in a local vector store. On every new run, the agent
   retrieves the most similar past winners and injects them as few-shot
   examples. The quality bar therefore ratchets upward over time.

3. **It refuses to regress.** Winning outputs are captured into a *golden
   dataset*. Any change to the prompt is checked against that dataset before it
   is allowed to drive real runs: if quality drops by more than a tolerance on
   any known-good brief, the change fails.

The result is a closed feedback loop where generation, evaluation, memory, and
prompt versioning reinforce each other.

---

## Architecture

A single run flows through `agent/core.py`:

1. Retrieve top-3 high-scoring past outputs (`agent/memory.py`, ChromaDB)
2. Inject them as few-shot examples (`agent/prompts.py`)
3. Generate headline / body / cta with Groq (`agent/tools.py`)
4. Judge each variant on 4 dimensions with Groq (`evals/judge.py`)
5. Store run + outputs + scores in SQLite (`db/store.py`)
6. Promote winners (>= 4.0) to golden + memory (`feedback/loop.py`)
7. Flag losers (< 2.5) for review (`feedback/loop.py`)

| Layer            | File(s)                          | Responsibility                                  |
|------------------|----------------------------------|-------------------------------------------------|
| Persistence      | `db/store.py`                    | SQLite: runs, outputs, golden, flagged          |
| Prompts          | `agent/prompts.py`               | All prompt text, versioned; nothing hardcoded elsewhere |
| Memory           | `agent/memory.py`                | ChromaDB + sentence-transformers retrieval      |
| Agent loop       | `agent/core.py`, `agent/tools.py`| Orchestration + Groq client                     |
| Evaluation       | `evals/*.py`                     | Rubric, judge, golden dataset, regression runner|
| Feedback         | `feedback/loop.py`               | Promote winners, flag losers                    |
| API              | `api/main.py`                    | `POST /run`                                      |
| CLI / tests      | `scripts/run_eval.py`, `tests/`  | Manual runs and the regression suite            |

---

## Setup

### Requirements
- Python 3.11+
- A Groq API key (free at <https://console.groq.com/keys>)

### Install

```bash
python -m venv .venv
# Windows:  .venv\Scripts\activate
# macOS/Linux:  source .venv/bin/activate

pip install -r requirements.txt
```

### Configure

```bash
cp .env.example .env          # Windows: copy .env.example .env
# then edit .env and set GROQ_API_KEY
```

Only `GROQ_API_KEY` is required. Everything else (SQLite at `./agent.db`,
ChromaDB at `./chroma_db`) is local; no other external services.

### First run

```bash
# Run the agent on the built-in FitFuel example brief:
python scripts/run_eval.py run

# Or run on your own brief:
python scripts/run_eval.py run --brief my_brief.json

# Inspect golden / flagged counts at any time:
python scripts/run_eval.py status
```

The very first run retrieves zero few-shot examples (memory is empty). As you
run more briefs, winners accumulate and later runs start standing on the
shoulders of earlier ones.

A brief is a JSON object:

```json
{
  "brand": "FitFuel",
  "product": "High-protein meal replacement shake",
  "audience": "Busy professionals aged 25-40",
  "tone": "Energetic and no-nonsense",
  "goal": "Drive trial purchases"
}
```

### Run the API

```bash
uvicorn api.main:app --reload
```

Then trigger the full loop:

```bash
curl -X POST http://127.0.0.1:8000/run \
  -H "Content-Type: application/json" \
  -d '{"brand":"FitFuel","product":"High-protein meal replacement shake","audience":"Busy professionals aged 25-40","tone":"Energetic and no-nonsense","goal":"Drive trial purchases"}'
```

The response contains the three generated variants, all four dimension scores
per variant, the weighted average, and a feedback summary (what was promoted /
flagged).

---

## How the self-improving loop works

1. **Retrieve.** The incoming brief is embedded (locally, via
   `all-MiniLM-L6-v2`) and used to query ChromaDB for the **top-3 most similar
   past outputs that scored >= 3.5/5**. Only proven-good copy is ever retrieved.

2. **Generate.** Those examples are injected into the active generation prompt
   under a *"Past high-performing examples"* section, and the model produces a
   headline hook, body copy, and a CTA in one structured JSON response.

3. **Evaluate.** Each of the three variants is immediately scored by the judge
   model on the four rubric dimensions. Scores are clamped to 1-5 and a weighted
   average is computed for internal ranking only.

4. **Log.** The run, every variant, and every dimension score are written to
   SQLite.

5. **Improve.** The feedback loop:
   - promotes any output with a weighted average **>= 4.0** into both the golden
     dataset and ChromaDB memory (so it can be retrieved next time);
   - flags any output **< 2.5** into the `flagged_outputs` table with the reason
     *"below quality threshold."*

Because winners re-enter memory, the pool of few-shot exemplars improves run
over run; that is the "self-improving" part.

---

## Evaluation & regression tests

### The rubric (`evals/rubric.py`)
Four dimensions, each 1-5:

| Dimension          | Question                                            | Weight |
|--------------------|-----------------------------------------------------|:------:|
| `hook_strength`    | Does the headline immediately grab attention?       | 0.30   |
| `brand_alignment`  | Does the copy reflect the brief tone and audience?  | 0.25   |
| `clarity`          | Is the message immediately understandable?          | 0.25   |
| `conversion_intent`| Does it drive toward the stated goal?               | 0.20   |

The weighted average is **internal only**, used for thresholds and ranking.
All four raw dimensions are always stored separately.

### Golden dataset (`evals/golden.py`)
Any output with weighted average **>= 4.0** is captured (brief, output, all
scores, prompt version, timestamp). This is the regression baseline.

### Regression runner (`evals/runner.py`)
For each golden entry it regenerates copy for the same brief + variant using the
prompt version under test, re-judges it, and compares the new weighted score to
the stored baseline. If any entry **drops by more than 0.5**, the run fails with
a clear warning.

```bash
# Run the regression eval against the active prompt and print a Rich table:
python scripts/run_eval.py regression
```

### Pytest suite (`tests/test_regression.py`)

```bash
pytest tests/test_regression.py
```

It loads the golden dataset, runs the eval runner, and asserts no entry
regresses more than 0.5 from baseline. The test **skips** (rather than failing
spuriously) when `GROQ_API_KEY` is unset or the golden dataset is still empty.

---

## Prompt versioning & how to swap versions safely

All prompt text lives in `agent/prompts.py`; nothing is hardcoded anywhere
else. Each prompt is a named, versioned constant (`GENERATION_PROMPT_V1`,
`GENERATION_PROMPT_V2`, ...). A single constant selects which is live:

```python
ACTIVE_PROMPT_VERSION = "GENERATION_PROMPT_V1"
```

Every run logs the version it used (stored on the run and on each output).

**To promote a new prompt safely:**

1. Add a new constant (e.g. `GENERATION_PROMPT_V2`) and register it in
   `PROMPT_REGISTRY`.
2. Run the regression check against it **before** making it active:
   ```bash
   # Either run the suite, or the CLI regression command after flipping the
   # constant in a branch:
   pytest tests/test_regression.py
   python scripts/run_eval.py regression
   ```
3. Only if no golden entry regresses more than 0.5, change
   `ACTIVE_PROMPT_VERSION` to the new version.

This is what "changing the active version triggers a regression check before it
is used in a real run" means in practice: the golden dataset is the gate.
`GENERATION_PROMPT_V2` ships in this repo as a worked example you can promote.

---

## Design Decisions

**Why ChromaDB for memory.** The agent needs *semantic* retrieval: "find past
briefs like this one", not exact lookups. ChromaDB gives a persistent local
vector store with cosine similarity and zero external services, and it pairs
cleanly with local sentence-transformers embeddings. SQLite alone can't do
nearest-neighbour search over brief semantics; a hosted vector DB would violate
the "local only" constraint and add ops overhead for no benefit at this scale.

**Why dimension scoring over a composite score.** A single 1-10 "quality" score
is unactionable and easy for a judge to anchor on. Scoring four independent
dimensions tells you *why* copy is weak (great hook, poor clarity) and makes the
signal far more stable and debuggable. We do compute a weighted average, but
only for internal thresholds/ranking; the four raw dimensions are always
stored, so we never lose information by collapsing too early.

**Why SQLite for eval storage.** Eval results are structured, relational, and
queryable (runs -> outputs -> scores; golden; flagged). SQLite gives ACID
guarantees, trivial setup, a single-file database, and real SQL, ideal for run
history and a golden dataset. It needs no server and ships with Python. A hosted
DB would add infrastructure with no upside for a local, single-node harness.

**Why the 4.0 threshold for golden inclusion.** On a 1-5 scale, 4.0 means
"clearly good on the weighted blend" without demanding perfection. Set it lower
and the golden set fills with mediocre copy, weakening both the regression
baseline and the few-shot exemplars. Set it higher (e.g. 4.5) and you rarely
capture anything, so the system never accumulates a baseline or improves. 4.0 is
the point where entries are good enough to *defend* against regressions and to
*teach* future runs. (The retrieval floor is a more permissive 3.5 so memory can
draw on a slightly wider pool of solid examples, while only the strongest >=4.0
outputs become protected golden baselines.)

---

## Project layout

```
self-improving-agent/
├── README.md
├── requirements.txt
├── .env.example
├── agent/        core loop, tools, memory, versioned prompts
├── evals/        rubric, LLM judge, golden dataset, regression runner
├── feedback/     post-run promote/flag loop
├── db/           SQLite store
├── api/          FastAPI app (POST /run)
├── tests/        pytest regression suite
└── scripts/      run_eval.py CLI (run / regression / status)
```
