from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path

from .agent_review import AgentReviewRequest, result_to_dict, result_to_markdown, review_agent
from .evaluator import evaluate
from .logger import append_log
from .models import EvaluationRequest


def load_json(path: str | None) -> dict:
    if not path or path == "-":
        return json.load(sys.stdin)
    with Path(path).expanduser().open("r", encoding="utf-8") as f:
        return json.load(f)


def cmd_evaluate(args: argparse.Namespace) -> int:
    data = load_json(args.input)
    data.setdefault("evaluation_type", args.type)
    request = EvaluationRequest.from_dict(data)
    result = evaluate(request)
    if args.log:
        append_log(result, args.log)
    print(json.dumps(asdict(result), ensure_ascii=False, indent=2))
    return 0


def cmd_review_agent(args: argparse.Namespace) -> int:
    data = load_json(args.input)
    request = AgentReviewRequest.from_dict(data)
    result = review_agent(request)
    output_format = args.format or request.output_preferences.get("format", "markdown_with_json")
    if output_format == "json":
        print(json.dumps(result_to_dict(result), ensure_ascii=False, indent=2))
    else:
        print(result_to_markdown(result))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="driftguard", description="Agent Drift evaluation CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    evaluate_parser = sub.add_parser("evaluate", help="Run an evaluation")
    evaluate_parser.add_argument("--type", required=True, choices=["goal", "instruction", "tool", "memory", "final"])
    evaluate_parser.add_argument("--input", "-i", required=True, help="JSON input file path or '-' for stdin")
    evaluate_parser.add_argument("--log", default=None, help="Optional JSONL log path")
    evaluate_parser.set_defaults(func=cmd_evaluate)

    review_parser = sub.add_parser("review-agent", help="Run an Agent-style DriftGuard review")
    review_parser.add_argument("--input", "-i", required=True, help="Agent review JSON input file path or '-' for stdin")
    review_parser.add_argument("--format", choices=["markdown", "json", "markdown_with_json"], default=None)
    review_parser.set_defaults(func=cmd_review_agent)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
