from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
import sys

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from scripts.summarize_runs import validate_run_history
from scripts.validate_daily import validate_daily


@dataclass(frozen=True)
class CheckResult:
    name: str
    ok: bool
    detail: str


def _result(name: str, ok: bool, detail: str) -> CheckResult:
    return CheckResult(name=name, ok=ok, detail=detail)


def _daily_workflow_check(root: Path) -> CheckResult:
    path = root / ".github" / "workflows" / "daily.yml"
    if not path.exists():
        return _result("daily workflow", False, f"missing workflow: {path}")
    workflow = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    try:
        steps = workflow["jobs"]["generate"]["steps"]
    except (KeyError, TypeError):
        return _result("daily workflow", False, "missing jobs.generate.steps")

    by_name = {
        step.get("name"): step
        for step in steps
        if isinstance(step, dict) and step.get("name")
    }
    required_steps = [
        "Validate LLM secret",
        "Generate digest",
        "Validate generated digest",
        "Commit generated files",
    ]
    missing = [name for name in required_steps if name not in by_name]
    if missing:
        return _result("daily workflow", False, "missing step(s): " + ", ".join(missing))

    generate = by_name["Generate digest"]
    validate = by_name["Validate generated digest"]
    commit = by_name["Commit generated files"]
    checks = [
        ("--require-llm", generate.get("run", "")),
        ("CSTCLOUD_API_KEY", str(generate.get("env", {}))),
        ("WOS_API_KEY", str(generate.get("env", {}))),
        ("scripts/validate_daily.py", validate.get("run", "")),
        ("git add -f data/runs data/state", commit.get("run", "")),
        ("git pull --rebase --autostash origin main", commit.get("run", "")),
    ]
    missing_text = [needle for needle, haystack in checks if needle not in haystack]
    if missing_text:
        return _result("daily workflow", False, "missing workflow guard: " + ", ".join(missing_text))

    concurrency = workflow.get("concurrency") or {}
    if concurrency.get("group") != "ecobio-daily" or concurrency.get("cancel-in-progress") is not False:
        return _result("daily workflow", False, "missing ecobio-daily non-cancelling concurrency")

    return _result("daily workflow", True, "daily workflow guards are present")


def _secret_docs_check(root: Path) -> CheckResult:
    paths = [root / "README.md", root / "docs" / "operations.md"]
    missing_paths = [str(path) for path in paths if not path.exists()]
    if missing_paths:
        return _result("secret documentation", False, "missing doc(s): " + ", ".join(missing_paths))
    combined = "\n".join(path.read_text(encoding="utf-8") for path in paths)
    required = ["CSTCLOUD_API_KEY", "WOS_API_KEY", "scripts/validate_daily.py", "data/state/seen_dois.json"]
    missing = [text for text in required if text not in combined]
    if missing:
        return _result("secret documentation", False, "missing doc text: " + ", ".join(missing))
    return _result("secret documentation", True, "secret and validation docs are present")


def _daily_artifacts_check(root: Path, digest_date: str) -> CheckResult:
    try:
        validate_daily(root, digest_date)
    except SystemExit as error:
        return _result("daily artifacts", False, str(error))
    return _result("daily artifacts", True, f"artifacts validate for {digest_date}")


def _run_history_check(root: Path, since: str) -> CheckResult:
    try:
        validate_run_history(root, since=since)
    except SystemExit as error:
        return _result("run history", False, str(error))
    return _result("run history", True, f"run history validates since {since}")


def check_operations(root: Path, digest_date: str, since: str) -> list[CheckResult]:
    return [
        _daily_workflow_check(root),
        _secret_docs_check(root),
        _daily_artifacts_check(root, digest_date),
        _run_history_check(root, since),
    ]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Check EcoBio Daily operational readiness.")
    parser.add_argument("--output-root", default=".")
    parser.add_argument("--date", required=True, help="Digest date to validate.")
    parser.add_argument("--since", required=True, help="Run history start date.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    results = check_operations(Path(args.output_root), digest_date=args.date, since=args.since)
    for result in results:
        status = "OK" if result.ok else "FAIL"
        print(f"{status}\t{result.name}\t{result.detail}")
    if not all(result.ok for result in results):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
