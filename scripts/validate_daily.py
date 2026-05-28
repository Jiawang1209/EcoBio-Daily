from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def _fail(message: str) -> None:
    raise SystemExit(message)


def _stage(metrics: dict[str, Any], name: str) -> dict[str, Any]:
    stage = metrics.get("stages", {}).get(name)
    if not isinstance(stage, dict):
        _fail(f"missing metrics stage: {name}")
    return stage


def validate_daily(
    output_root: Path,
    digest_date: str,
    min_items: int = 5,
    max_items: int = 8,
) -> None:
    metrics_path = output_root / "data" / "runs" / f"{digest_date}.json"
    if not metrics_path.exists():
        _fail(f"missing metrics file: {metrics_path}")
    try:
        metrics = json.loads(metrics_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        _fail(f"invalid metrics JSON: {error}")

    build = _stage(metrics, "build_digest")
    items = int(build.get("items", -1))
    if not min_items <= items <= max_items:
        _fail(f"expected {min_items}-{max_items} digest items, got {items}")

    grounding = _stage(metrics, "llm_grounding")
    failed = int(grounding.get("failed", 0))
    errored = int(grounding.get("errored", 0))
    if failed or errored:
        _fail(f"grounding check failed: failed={failed}, errored={errored}")

    output = _stage(metrics, "output")
    for key in ("zh", "en"):
        relative = output.get(key)
        if not isinstance(relative, str) or not relative:
            _fail(f"missing output path in metrics: {key}")
        path = output_root / relative
        if not path.exists():
            _fail(f"missing output file: {path}")

    state_path = output_root / "data" / "state" / "seen_dois.json"
    if not state_path.exists():
        _fail(f"missing seen DOI state: {state_path}")
    try:
        state = json.loads(state_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        _fail(f"invalid seen DOI state JSON: {error}")
    if not isinstance(state, dict):
        _fail("invalid seen DOI state: expected JSON object")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate generated EcoBio Daily artifacts.")
    parser.add_argument("--date", required=True, help="Digest date in YYYY-MM-DD format.")
    parser.add_argument("--output-root", default=".", help="Directory where artifacts were written.")
    parser.add_argument("--min-items", type=int, default=5)
    parser.add_argument("--max-items", type=int, default=8)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    validate_daily(
        output_root=Path(args.output_root),
        digest_date=args.date,
        min_items=args.min_items,
        max_items=args.max_items,
    )
    print(f"Validated EcoBio Daily artifacts for {args.date}.")


if __name__ == "__main__":
    main()
