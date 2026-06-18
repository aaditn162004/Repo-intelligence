#!/usr/bin/env python3
"""
Hand-rolled evals harness for RepoIntel.

For each JSON test case it:
  1. ensures the case's repository is indexed on the target RepoIntel API
     (reusing an already-indexed repo when one exists, otherwise indexing it),
  2. asks the case's question via POST /api/v1/query (non-streaming),
  3. scores the answer with an LLM-as-judge (Groq) against the expected facts,
  4. writes a Markdown report with overall pass rate and a per-category breakdown.

No LangSmith / Braintrust — just httpx, the Groq REST API, and the stdlib.

Usage:
    export GROQ_API_KEY=gsk_...
    export REPOINTEL_API_URL=https://aaditn-repointel-api.hf.space   # optional
    python run_evals.py
    python run_evals.py --category multi_hop --limit 3
    python run_evals.py --no-index            # assume repos are already indexed

A case PASSES when its coverage score >= EVAL_PASS_THRESHOLD (default 1.0, i.e.
every expected fact must be supported). Override with --pass-threshold or the
EVAL_PASS_THRESHOLD env var.
"""

from __future__ import annotations

import argparse
import glob
import json
import os
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

import httpx

from judge import DEFAULT_JUDGE_MODEL, JudgeResult, judge_answer

HERE = Path(__file__).parent
TERMINAL_STATUSES = {"ready", "failed"}


def _load_dotenv(path: Path) -> None:
    """Load KEY=VALUE pairs from a local .env into os.environ (no extra deps).

    Existing environment variables win, so an explicit `export` always overrides
    the file. The file is gitignored — put your real GROQ_API_KEY there.
    """
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key, value = key.strip(), value.strip().strip("'\"")
        if key and key not in os.environ:
            os.environ[key] = value


_load_dotenv(HERE / ".env")
DEFAULT_API_URL = os.environ.get("REPOINTEL_API_URL", "https://aaditn-repointel-api.hf.space")


# ---------------------------------------------------------------------------
# Test cases
# ---------------------------------------------------------------------------


@dataclass
class TestCase:
    id: str
    category: str
    repo_url: str
    question: str
    expected_facts: List[str]
    branch: str = "main"
    path: Optional[str] = None

    @classmethod
    def from_file(cls, path: str) -> "TestCase":
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        missing = {"id", "category", "repo_url", "question", "expected_facts"} - data.keys()
        if missing:
            raise ValueError(f"{path}: missing required fields {sorted(missing)}")
        return cls(
            id=data["id"],
            category=data["category"],
            repo_url=data["repo_url"],
            question=data["question"],
            expected_facts=data["expected_facts"],
            branch=data.get("branch", "main"),
            path=path,
        )


def load_cases(cases_dir: Path, category: Optional[str], limit: Optional[int]) -> List[TestCase]:
    files = sorted(glob.glob(str(cases_dir / "*.json")))
    cases = [TestCase.from_file(f) for f in files]
    if category:
        cases = [c for c in cases if c.category == category]
    if limit:
        cases = cases[:limit]
    return cases


# ---------------------------------------------------------------------------
# RepoIntel API client
# ---------------------------------------------------------------------------


class RepoIntelClient:
    def __init__(self, base_url: str, *, timeout: float = 240.0):
        self.base = base_url.rstrip("/") + "/api/v1"
        self._http = httpx.Client(timeout=timeout)

    def list_repositories(self) -> List[dict]:
        r = self._http.get(f"{self.base}/repositories")
        r.raise_for_status()
        return r.json()

    def get_repository(self, repo_id: str) -> dict:
        r = self._http.get(f"{self.base}/repositories/{repo_id}")
        r.raise_for_status()
        return r.json()

    def create_repository(self, url: str, branch: str) -> dict:
        r = self._http.post(
            f"{self.base}/repositories", json={"url": url, "branch": branch}
        )
        r.raise_for_status()
        return r.json()

    def query(self, repo_id: str, question: str, top_k: int = 10) -> dict:
        r = self._http.post(
            f"{self.base}/query",
            json={
                "repository_id": repo_id,
                "question": question,
                "max_context_chunks": top_k,
                "stream": False,
            },
        )
        r.raise_for_status()
        return r.json()

    def close(self) -> None:
        self._http.close()


def ensure_indexed(
    client: RepoIntelClient,
    url: str,
    branch: str,
    *,
    do_index: bool,
    cache: Dict[str, str],
    index_timeout: float = 900.0,
    poll_interval: float = 6.0,
) -> str:
    """Return a repo_id for (url, branch) whose status is `ready`.

    Reuses an already-indexed repo if one exists; otherwise (when do_index) kicks
    off indexing and polls until ready. `cache` dedupes within a single run so a
    repo shared by many cases is only indexed once.
    """
    key = f"{url}@{branch}"
    if key in cache:
        return cache[key]

    # Reuse an existing ready repo for this URL+branch.
    for repo in client.list_repositories():
        if repo.get("url") == url and repo.get("branch") == branch and repo.get("status") == "ready":
            cache[key] = repo["id"]
            return repo["id"]

    if not do_index:
        raise RuntimeError(
            f"No ready repository for {key} and --no-index was set. "
            f"Index it first or drop --no-index."
        )

    print(f"    indexing {key} ...", flush=True)
    repo = client.create_repository(url, branch)
    repo_id = repo["id"]

    deadline = time.time() + index_timeout
    last_status = ""
    while time.time() < deadline:
        info = client.get_repository(repo_id)
        status = info.get("status", "")
        if status != last_status:
            print(f"      status: {status}", flush=True)
            last_status = status
        if status == "ready":
            cache[key] = repo_id
            return repo_id
        if status == "failed":
            raise RuntimeError(f"indexing failed: {info.get('error_message')}")
        time.sleep(poll_interval)

    raise TimeoutError(f"indexing {key} did not finish within {index_timeout:.0f}s")


# ---------------------------------------------------------------------------
# Running a single case
# ---------------------------------------------------------------------------


@dataclass
class CaseResult:
    case: TestCase
    passed: bool = False
    score: float = 0.0
    answer: str = ""
    judge: Optional[JudgeResult] = None
    latency_s: float = 0.0
    error: Optional[str] = None


def run_case(
    case: TestCase,
    client: RepoIntelClient,
    *,
    groq_key: str,
    judge_model: str,
    pass_threshold: float,
    do_index: bool,
    repo_cache: Dict[str, str],
) -> CaseResult:
    result = CaseResult(case=case)
    started = time.time()
    try:
        repo_id = ensure_indexed(
            client, case.repo_url, case.branch, do_index=do_index, cache=repo_cache
        )
        response = client.query(repo_id, case.question)
        result.answer = response.get("answer", "")

        judged = judge_answer(
            case.question,
            result.answer,
            case.expected_facts,
            api_key=groq_key,
            model=judge_model,
        )
        result.judge = judged
        result.score = judged.score
        result.passed = judged.score >= pass_threshold
    except Exception as exc:  # noqa: BLE001 - one bad case shouldn't abort the suite
        result.error = f"{type(exc).__name__}: {exc}"
    finally:
        result.latency_s = time.time() - started
    return result


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------


def _pct(n: int, d: int) -> str:
    return f"{(100.0 * n / d):.0f}%" if d else "—"


def render_report(
    results: List[CaseResult],
    *,
    api_url: str,
    judge_model: str,
    pass_threshold: float,
) -> str:
    total = len(results)
    passed = sum(1 for r in results if r.passed)
    errored = sum(1 for r in results if r.error)
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    lines: List[str] = []
    lines.append("# RepoIntel Eval Report")
    lines.append("")
    lines.append(f"- **Run:** {now}")
    lines.append(f"- **API:** {api_url}")
    lines.append(f"- **Judge:** {judge_model} (LLM-as-judge, Groq)")
    lines.append(f"- **Pass threshold:** coverage ≥ {pass_threshold:.2f}")
    lines.append(f"- **Overall:** {passed}/{total} passed ({_pct(passed, total)})")
    if errored:
        lines.append(f"- **Errored:** {errored} case(s) — see details below")
    lines.append("")

    # Per-category breakdown.
    cats: Dict[str, List[CaseResult]] = {}
    for r in results:
        cats.setdefault(r.case.category, []).append(r)

    lines.append("## By category")
    lines.append("")
    lines.append("| Category | Cases | Passed | Pass rate | Avg coverage |")
    lines.append("|----------|-------|--------|-----------|--------------|")
    for cat in sorted(cats):
        rs = cats[cat]
        c_pass = sum(1 for r in rs if r.passed)
        avg = sum(r.score for r in rs) / len(rs)
        lines.append(f"| {cat} | {len(rs)} | {c_pass} | {_pct(c_pass, len(rs))} | {avg:.0%} |")
    lines.append("")

    # Per-case details.
    lines.append("## Cases")
    lines.append("")
    for r in results:
        status = "✅ PASS" if r.passed else ("⚠️ ERROR" if r.error else "❌ FAIL")
        lines.append(f"### {status} — `{r.case.id}` ({r.case.category})")
        lines.append("")
        lines.append(f"- **Repo:** {r.case.repo_url} @ {r.case.branch}")
        lines.append(f"- **Question:** {r.case.question}")
        lines.append(f"- **Coverage:** {r.score:.0%} · **Latency:** {r.latency_s:.1f}s")
        if r.error:
            lines.append(f"- **Error:** `{r.error}`")
        if r.judge:
            lines.append("- **Facts:**")
            for v in r.judge.verdicts:
                mark = "✓" if v.supported else "✗"
                lines.append(f"  - {mark} {v.fact} — _{v.evidence}_")
        if r.answer:
            snippet = r.answer.strip()
            if len(snippet) > 1200:
                snippet = snippet[:1200] + " …(truncated)"
            lines.append("")
            lines.append("<details><summary>Answer</summary>")
            lines.append("")
            lines.append(snippet)
            lines.append("")
            lines.append("</details>")
        lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main() -> int:
    parser = argparse.ArgumentParser(description="Run RepoIntel evals.")
    parser.add_argument("--api-url", default=DEFAULT_API_URL, help="RepoIntel API base URL")
    parser.add_argument("--cases-dir", default=str(HERE / "cases"), help="Directory of case JSON")
    parser.add_argument("--out-dir", default=str(HERE / "reports"), help="Report output dir")
    parser.add_argument("--category", choices=["factual", "structural", "multi_hop"], default=None)
    parser.add_argument("--limit", type=int, default=None, help="Run only the first N cases")
    parser.add_argument("--judge-model", default=DEFAULT_JUDGE_MODEL)
    parser.add_argument(
        "--pass-threshold",
        type=float,
        default=float(os.environ.get("EVAL_PASS_THRESHOLD", "1.0")),
    )
    parser.add_argument(
        "--no-index",
        action="store_true",
        help="Do not index repos; require them to already be ready on the API",
    )
    args = parser.parse_args()

    groq_key = os.environ.get("GROQ_API_KEY", "").strip()
    if not groq_key:
        print("ERROR: GROQ_API_KEY is not set (needed for the LLM-as-judge).", file=sys.stderr)
        return 2

    cases = load_cases(Path(args.cases_dir), args.category, args.limit)
    if not cases:
        print(f"No cases found in {args.cases_dir} (category={args.category}).", file=sys.stderr)
        return 2

    print(f"Running {len(cases)} case(s) against {args.api_url}")
    print(f"Judge: {args.judge_model} · pass threshold: {args.pass_threshold:.2f}\n")

    client = RepoIntelClient(args.api_url)
    repo_cache: Dict[str, str] = {}
    results: List[CaseResult] = []
    try:
        for i, case in enumerate(cases, start=1):
            print(f"[{i}/{len(cases)}] {case.id} ({case.category}) ...", flush=True)
            result = run_case(
                case,
                client,
                groq_key=groq_key,
                judge_model=args.judge_model,
                pass_threshold=args.pass_threshold,
                do_index=not args.no_index,
                repo_cache=repo_cache,
            )
            results.append(result)
            if result.error:
                print(f"    ERROR: {result.error}", flush=True)
            else:
                tag = "PASS" if result.passed else "FAIL"
                print(f"    {tag} · coverage {result.score:.0%} · {result.latency_s:.1f}s", flush=True)
    finally:
        client.close()

    report = render_report(
        results,
        api_url=args.api_url,
        judge_model=args.judge_model,
        pass_threshold=args.pass_threshold,
    )

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    out_path = out_dir / f"report-{stamp}.md"
    out_path.write_text(report, encoding="utf-8")

    passed = sum(1 for r in results if r.passed)
    print(f"\n{passed}/{len(results)} passed ({_pct(passed, len(results))}). Report: {out_path}")

    # Non-zero exit if anything failed/errored — handy for CI gating later.
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
