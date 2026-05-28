from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def _stage(metrics: dict[str, Any], name: str) -> dict[str, Any]:
    stage = metrics.get("stages", {}).get(name)
    return stage if isinstance(stage, dict) else {}


def _int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def load_run_summaries(output_root: Path) -> list[dict[str, Any]]:
    run_dir = output_root / "data" / "runs"
    rows: list[dict[str, Any]] = []
    for path in sorted(run_dir.glob("*.json")):
        try:
            metrics = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        build = _stage(metrics, "build_digest")
        grounding = _stage(metrics, "llm_grounding")
        relevance = _stage(metrics, "llm_relevance")
        keyword = _stage(metrics, "keyword_score")
        fetch = _stage(metrics, "fetch_total")
        rows.append(
            {
                "date": str(metrics.get("date") or path.stem),
                "items": _int(build.get("items"), -1),
                "sections": _int(build.get("sections"), 0),
                "highlights": _int(build.get("highlights"), 0),
                "llm_candidates": _int(relevance.get("candidates"), 0),
                "llm_kept": _int(relevance.get("kept"), 0),
                "backfilled": _int(relevance.get("backfilled"), 0),
                "grounding_failed": _int(grounding.get("failed"), 0),
                "grounding_errored": _int(grounding.get("errored"), 0),
                "keyword_above_threshold": _int(keyword.get("above_threshold"), 0),
                "fetched": _int(fetch.get("total"), 0),
                "duration_seconds": metrics.get("duration_seconds"),
            }
        )
    return sorted(rows, key=lambda row: row["date"])


def validate_run_history(
    output_root: Path,
    since: str,
    min_items: int = 5,
    max_items: int = 8,
) -> None:
    rows = [row for row in load_run_summaries(output_root) if row["date"] >= since]
    if not rows:
        raise SystemExit(f"no run metrics found since {since}")
    failures: list[str] = []
    for row in rows:
        if not min_items <= row["items"] <= max_items:
            failures.append(
                f"{row['date']}: expected {min_items}-{max_items} items, got {row['items']}"
            )
        if row["grounding_failed"] or row["grounding_errored"]:
            failures.append(
                f"{row['date']}: grounding failures failed={row['grounding_failed']} errored={row['grounding_errored']}"
            )
    if failures:
        raise SystemExit("\n".join(failures))


def _print_table(rows: list[dict[str, Any]]) -> None:
    headers = [
        "date",
        "items",
        "llm_kept",
        "backfilled",
        "grounding_failed",
        "grounding_errored",
        "fetched",
        "keyword_above_threshold",
    ]
    print("\t".join(headers))
    for row in rows:
        print("\t".join(str(row.get(header, "")) for header in headers))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Summarize EcoBio Daily run metrics.")
    parser.add_argument("--output-root", default=".")
    parser.add_argument("--since", help="Validate runs on or after YYYY-MM-DD.")
    parser.add_argument("--min-items", type=int, default=5)
    parser.add_argument("--max-items", type=int, default=8)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    output_root = Path(args.output_root)
    rows = load_run_summaries(output_root)
    _print_table(rows)
    if args.since:
        validate_run_history(
            output_root,
            since=args.since,
            min_items=args.min_items,
            max_items=args.max_items,
        )
        print(f"Run history validated since {args.since}.")


if __name__ == "__main__":
    main()
