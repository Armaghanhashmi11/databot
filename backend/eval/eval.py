"""Simple eval harness: runs the 10 questions in questions.json against one
or more models and writes a markdown comparison table (accuracy + latency)
to eval/results.md.

Usage:
    python eval/eval.py
    python eval/eval.py --models ollama:qwen2.5:7b ollama:llama3.1:8b anthropic:claude-opus-5

Scoring is intentionally simple (this is explicitly a "simple eval script"):
numeric questions check whether any number in the agent's answer text is
within `tolerance` of the expected value; text questions check whether the
expected keyword(s) appear in the answer (case-insensitive).
"""
from __future__ import annotations

import argparse
import json
import re
import statistics
import sys
import time
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from v2.agent import run_agent  # noqa: E402
from v2.llm import MissingAPIKeyError, UnknownProviderError  # noqa: E402
from v2.session import AgentSession  # noqa: E402

HERE = Path(__file__).resolve().parent
DEFAULT_CSV = HERE / "sample_data.csv"
DEFAULT_QUESTIONS = HERE / "questions.json"
DEFAULT_RESULTS = HERE / "results.md"

_NUMBER_RE = re.compile(r"-?\d[\d,]*\.?\d*")


@dataclass
class QuestionResult:
    question_id: int
    question: str
    answer: str
    correct: bool
    latency_ms: float
    error: str | None = None


def _extract_numbers(text: str) -> list[float]:
    numbers = []
    for raw in _NUMBER_RE.findall(text):
        cleaned = raw.replace(",", "").strip(".")
        if cleaned in {"", "-"}:
            continue
        try:
            numbers.append(float(cleaned))
        except ValueError:
            continue
    return numbers


def score_answer(spec: dict, answer_text: str) -> bool:
    if spec["type"] == "numeric":
        found = _extract_numbers(answer_text)
        return any(abs(n - spec["value"]) <= spec.get("tolerance", 0) for n in found)

    keywords = spec["keywords"]
    lowered = answer_text.lower()
    hits = [kw.lower() in lowered for kw in keywords]
    return all(hits) if spec.get("match") == "all" else any(hits)


def run_one_model(
    provider: str, model: str, questions: list[dict], csv_path: Path
) -> list[QuestionResult]:
    results = []
    for spec in questions:
        # Fresh session per question so each gets its own SQL table and no
        # state leaks between questions.
        session = AgentSession.from_csv(
            csv_path, session_id=f"eval_{provider}_{model}_{spec['id']}".replace(":", "_")
        )
        start = time.perf_counter()
        try:
            answer = run_agent(session, spec["question"], provider=provider, model=model)
            latency_ms = (time.perf_counter() - start) * 1000
            correct = score_answer(spec, answer.answer)
            results.append(
                QuestionResult(spec["id"], spec["question"], answer.answer, correct, latency_ms)
            )
        except (UnknownProviderError, MissingAPIKeyError) as e:
            results.append(QuestionResult(spec["id"], spec["question"], "", False, 0.0, error=str(e)))
        except Exception as e:  # noqa: BLE001 -- eval script must not die on one bad question
            latency_ms = (time.perf_counter() - start) * 1000
            results.append(
                QuestionResult(spec["id"], spec["question"], "", False, latency_ms, error=str(e))
            )
    return results


def summarize(label: str, results: list[QuestionResult]) -> dict:
    n = len(results)
    correct = sum(r.correct for r in results)
    latencies = [r.latency_ms for r in results if r.error is None]
    return {
        "label": label,
        "accuracy": correct / n if n else 0.0,
        "correct": correct,
        "total": n,
        "avg_latency_ms": statistics.mean(latencies) if latencies else float("nan"),
        "p50_latency_ms": statistics.median(latencies) if latencies else float("nan"),
        "errors": sum(1 for r in results if r.error),
    }


def render_markdown(summaries: list[dict], per_question: dict[str, list[QuestionResult]]) -> str:
    lines = [
        "# Eval Results",
        "",
        "## Summary",
        "",
        "| Model | Accuracy | Correct/Total | Avg Latency (ms) | p50 Latency (ms) | Errors |",
        "|---|---|---|---|---|---|",
    ]
    for s in summaries:
        avg = f"{s['avg_latency_ms']:.0f}" if s["avg_latency_ms"] == s["avg_latency_ms"] else "n/a"
        p50 = f"{s['p50_latency_ms']:.0f}" if s["p50_latency_ms"] == s["p50_latency_ms"] else "n/a"
        lines.append(
            f"| {s['label']} | {s['accuracy'] * 100:.0f}% | {s['correct']}/{s['total']} | "
            f"{avg} | {p50} | {s['errors']} |"
        )

    lines += ["", "## Per-question detail", ""]
    for label, results in per_question.items():
        lines.append(f"### {label}")
        lines.append("")
        lines.append("| # | Question | Correct | Latency (ms) | Answer |")
        lines.append("|---|---|---|---|---|")
        for r in results:
            answer_display = (r.error or r.answer).replace("|", "\\|").replace("\n", " ")
            if len(answer_display) > 160:
                answer_display = answer_display[:157] + "..."
            mark = "yes" if r.correct else "no"
            lines.append(
                f"| {r.question_id} | {r.question} | {mark} | {r.latency_ms:.0f} | {answer_display} |"
            )
        lines.append("")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run the 10-question eval against one or more models."
    )
    parser.add_argument("--csv", default=str(DEFAULT_CSV))
    parser.add_argument("--questions", default=str(DEFAULT_QUESTIONS))
    parser.add_argument("--out", default=str(DEFAULT_RESULTS))
    parser.add_argument(
        "--models",
        nargs="*",
        default=["ollama:qwen2.5:7b", "ollama:llama3.1:8b"],
        help="provider:model pairs, e.g. ollama:qwen2.5:7b anthropic:claude-opus-5",
    )
    args = parser.parse_args()

    questions = json.loads(Path(args.questions).read_text())
    summaries = []
    per_question = {}

    for spec in args.models:
        provider, _, model = spec.partition(":")
        label = f"{provider}/{model}"
        print(f"Running {len(questions)} questions against {label}...", file=sys.stderr)
        results = run_one_model(provider, model, questions, Path(args.csv))
        per_question[label] = results
        summaries.append(summarize(label, results))
        for r in results:
            status = "OK" if r.correct else ("ERR" if r.error else "WRONG")
            print(
                f"  [{status}] Q{r.question_id} ({r.latency_ms:.0f}ms): {r.answer[:80] or r.error}",
                file=sys.stderr,
            )

    markdown = render_markdown(summaries, per_question)
    Path(args.out).write_text(markdown, encoding="utf-8")
    print(f"\nWrote {args.out}", file=sys.stderr)
    print(markdown)


if __name__ == "__main__":
    main()
