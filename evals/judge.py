"""
LLM-as-judge scoring via Groq (LLaMA 3.1 8B by default — cheap and fast).

The judge receives the question, the system's answer, and the list of expected
facts. For each fact it decides whether the answer *states or clearly supports*
it (semantic match, not string match). The numeric score is computed in Python
from the per-fact verdicts — we never trust the model to do arithmetic.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import List

import httpx

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
DEFAULT_JUDGE_MODEL = "llama-3.1-8b-instant"

_SYSTEM_PROMPT = """You are a strict, fair evaluator for a code-understanding question-answering system.

You are given a QUESTION, an ANSWER produced by the system, and a numbered list of EXPECTED FACTS.
For each expected fact, decide whether the ANSWER states it or clearly supports it.

Rules:
- Judge meaning, not wording. Paraphrases, synonyms, and equivalent file paths count as supported.
- A fact is supported only if the ANSWER actually contains or directly implies it. Do not give credit
  for facts that are merely plausible but absent from the answer.
- Do not use any outside knowledge about the repository; judge strictly against the ANSWER text.

Respond with JSON only, in exactly this shape:
{
  "verdicts": [
    {"fact_index": 1, "supported": true, "evidence": "short quote or reason"},
    {"fact_index": 2, "supported": false, "evidence": "why it is missing"}
  ]
}
Include exactly one verdict object per expected fact, using 1-based fact_index."""


@dataclass
class FactVerdict:
    fact: str
    supported: bool
    evidence: str


@dataclass
class JudgeResult:
    verdicts: List[FactVerdict]
    raw: str  # raw judge JSON, kept for debugging / the report appendix

    @property
    def supported_count(self) -> int:
        return sum(1 for v in self.verdicts if v.supported)

    @property
    def total(self) -> int:
        return len(self.verdicts)

    @property
    def score(self) -> float:
        """Fraction of expected facts the answer covers, in [0, 1]."""
        return self.supported_count / self.total if self.total else 0.0


def _build_user_prompt(question: str, answer: str, expected_facts: List[str]) -> str:
    facts_block = "\n".join(f"{i}. {fact}" for i, fact in enumerate(expected_facts, start=1))
    return (
        f"QUESTION:\n{question}\n\n"
        f"ANSWER:\n{answer}\n\n"
        f"EXPECTED FACTS:\n{facts_block}\n"
    )


def judge_answer(
    question: str,
    answer: str,
    expected_facts: List[str],
    *,
    api_key: str,
    model: str = DEFAULT_JUDGE_MODEL,
    timeout: float = 60.0,
) -> JudgeResult:
    """Score one answer against its expected facts. Raises on API/transport failure."""
    if not expected_facts:
        return JudgeResult(verdicts=[], raw="")

    # An empty answer trivially supports nothing — skip the API call.
    if not answer or not answer.strip():
        return JudgeResult(
            verdicts=[FactVerdict(f, False, "answer was empty") for f in expected_facts],
            raw="",
        )

    payload = {
        "model": model,
        "temperature": 0,
        "response_format": {"type": "json_object"},
        "messages": [
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": _build_user_prompt(question, answer, expected_facts)},
        ],
    }

    resp = httpx.post(
        GROQ_URL,
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json=payload,
        timeout=timeout,
    )
    resp.raise_for_status()
    content = resp.json()["choices"][0]["message"]["content"]

    return _parse_verdicts(content, expected_facts)


def _parse_verdicts(content: str, expected_facts: List[str]) -> JudgeResult:
    """Map the judge's JSON back onto expected_facts by 1-based fact_index.

    Any fact the judge fails to return a verdict for is treated as unsupported,
    so a malformed/partial judge response can never inflate the score.
    """
    by_index: dict[int, dict] = {}
    try:
        data = json.loads(content)
        for v in data.get("verdicts", []):
            idx = v.get("fact_index")
            if isinstance(idx, int):
                by_index[idx] = v
    except (json.JSONDecodeError, AttributeError, TypeError):
        pass  # leave by_index empty -> everything unsupported

    verdicts: List[FactVerdict] = []
    for i, fact in enumerate(expected_facts, start=1):
        v = by_index.get(i, {})
        verdicts.append(
            FactVerdict(
                fact=fact,
                supported=bool(v.get("supported", False)),
                evidence=str(v.get("evidence", "no verdict returned by judge")),
            )
        )
    return JudgeResult(verdicts=verdicts, raw=content)
