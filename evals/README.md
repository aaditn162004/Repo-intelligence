# RepoIntel Evals

A small, hand-rolled evaluation harness for the RepoIntel API. No LangSmith,
no Braintrust — just `httpx`, the Groq REST API, and the standard library.

It indexes each test case's repository on a deployed RepoIntel instance, asks
the question through `POST /api/v1/query`, then uses an **LLM-as-judge** (Groq,
LLaMA 3.1 8B) to check whether the answer contains the expected facts. Output is
a Markdown report with overall pass rate and a per-category breakdown.

## Layout

```
evals/
├── run_evals.py     # the runner (indexing, querying, scoring, reporting)
├── judge.py         # LLM-as-judge against Groq
├── cases/           # one JSON file per test case
├── reports/         # generated Markdown reports (gitignored)
└── requirements.txt
```

## Setup

```bash
cd evals
pip install -r requirements.txt

export GROQ_API_KEY=gsk_...                                   # required (judge)
export REPOINTEL_API_URL=https://aaditn-repointel-api.hf.space  # optional; this is the default
```

## Run

```bash
python run_evals.py                      # all cases
python run_evals.py --category multi_hop # one category: factual | structural | multi_hop
python run_evals.py --limit 3            # first 3 cases only
python run_evals.py --no-index           # reuse already-indexed repos; never trigger indexing
python run_evals.py --pass-threshold 0.7 # looser pass bar (see Scoring)
```

The runner prints progress and writes `reports/report-<timestamp>.md`. It exits
non-zero if any case fails or errors, so it can gate CI later.

> The deployed backend runs on Hugging Face's free tier and sleeps when idle —
> the first call may take 30–60s, and indexing a fresh repo a few minutes. Repos
> already indexed (matched by URL + branch with status `ready`) are reused, and a
> repo shared by several cases is only indexed once per run.

## Test case format

One JSON object per file in `cases/`. The filename is just for humans; the `id`
field identifies the case in reports.

```json
{
  "id": "factual-001",
  "category": "factual",
  "repo_url": "https://github.com/psf/requests",
  "branch": "main",
  "question": "What is the top-level function for making an HTTP GET request, and which module defines it?",
  "expected_facts": [
    "The `get` function is the public helper for GET requests",
    "It is defined in requests/api.py",
    "It delegates to the generic `request()` function"
  ]
}
```

| Field | Required | Notes |
|-------|----------|-------|
| `id` | yes | Unique identifier shown in the report |
| `category` | yes | `factual`, `structural`, or `multi_hop` |
| `repo_url` | yes | GitHub URL to index and query against |
| `branch` | no | Defaults to `main` |
| `question` | yes | Natural-language question sent to RepoIntel |
| `expected_facts` | yes | Facts the answer should contain; the judge checks each one |

**Categories**
- `factual` — a single fact (a function, a file, a value).
- `structural` — how the codebase is organised (modules, layers, responsibilities).
- `multi_hop` — requires chaining several facts (e.g. tracing a call path).

## Scoring

For each case the judge returns a yes/no verdict per expected fact. The
**coverage score** is `supported_facts / total_facts`, computed in Python (the
model never does the arithmetic). A case **passes** when coverage ≥
`--pass-threshold` (default **1.0** — every fact must be supported). Lower it
with `--pass-threshold` or the `EVAL_PASS_THRESHOLD` env var.

The report shows the pass/fail per case, every fact verdict with the judge's
evidence, latency, and a collapsible copy of the full answer.

## Writing more cases

The 5 cases here (all against `psf/requests`) are starters that exercise each
category. Add your own by dropping more JSON files into `cases/`. Keep
`expected_facts` atomic and answerable from the code so the judge has a clear,
fair target — one idea per fact.
