"""Command-line entry point for governed disease-model evidence operations."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any

from .contracts import validate_dataset_manifest, validate_prediction_event
from .evaluation import build_evaluation_report
from .promotion import evaluate_promotion
from .rollback import execute_rollback_drill


def _load(path: str) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _emit(value: Any, output: str | None) -> None:
    rendered = json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n"
    if output is None:
        print(rendered, end="")
        return
    target = Path(output)
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_suffix(target.suffix + ".tmp")
    temporary.write_text(rendered, encoding="utf-8")
    os.replace(temporary, target)


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(description=__doc__)
    commands = root.add_subparsers(dest="command", required=True)

    dataset = commands.add_parser("validate-dataset")
    dataset.add_argument("manifest")
    dataset.add_argument("--output")

    event = commands.add_parser("validate-event")
    event.add_argument("event")
    event.add_argument("--output")

    evaluate = commands.add_parser("evaluate")
    evaluate.add_argument("records", help="JSON object with labels, lineage, and records")
    evaluate.add_argument("--bootstrap-iterations", type=int, default=200)
    evaluate.add_argument("--seed", type=int, default=41212)
    evaluate.add_argument("--output")

    promote = commands.add_parser("promote")
    promote.add_argument("evaluation")
    promote.add_argument("policy")
    promote.add_argument("evidence")
    promote.add_argument("--output")

    rollback = commands.add_parser("rollback-drill")
    rollback.add_argument("registry")
    rollback.add_argument("crop")
    rollback.add_argument("--trigger", default="SIMULATED_ARTIFACT_INTEGRITY_FAILURE")
    rollback.add_argument("--output")
    return root


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    if args.command == "validate-dataset":
        result = validate_dataset_manifest(_load(args.manifest))
    elif args.command == "validate-event":
        validate_prediction_event(_load(args.event))
        result = {"valid": True}
    elif args.command == "evaluate":
        payload = _load(args.records)
        result = build_evaluation_report(
            payload["records"], payload["labels"], payload["lineage"],
            bootstrap_iterations=args.bootstrap_iterations, seed=args.seed,
        )
    elif args.command == "promote":
        result = evaluate_promotion(_load(args.evaluation), _load(args.policy), _load(args.evidence))
    else:
        result = execute_rollback_drill(_load(args.registry), args.crop, trigger=args.trigger)
    _emit(result, args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
