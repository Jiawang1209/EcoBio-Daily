import json
from pathlib import Path

import pytest

from scripts.check_ops import check_operations


def _write_workflow(root: Path) -> None:
    workflow = root / ".github" / "workflows" / "daily.yml"
    workflow.parent.mkdir(parents=True)
    workflow.write_text(
        """
name: Generate EcoBio Daily
on:
  schedule:
    - cron: "0 0 * * *"
  workflow_dispatch:
    inputs:
      digest_date:
        required: false
concurrency:
  group: ecobio-daily
  cancel-in-progress: false
jobs:
  generate:
    steps:
      - name: Check out repository
        uses: actions/checkout@v6
      - name: Set up Python
        uses: actions/setup-python@v6
        with:
          python-version: "3.11"
      - name: Validate LLM secret
        env:
          CSTCLOUD_API_KEY: ${{ secrets.CSTCLOUD_API_KEY }}
        run: echo CSTCLOUD_API_KEY secret is not configured
      - name: Generate digest
        env:
          CSTCLOUD_API_KEY: ${{ secrets.CSTCLOUD_API_KEY }}
          WOS_API_KEY: ${{ secrets.WOS_API_KEY }}
        run: python scripts/run_daily.py --date "$DIGEST_DATE" --require-llm
      - name: Validate generated digest
        run: python scripts/validate_daily.py --date "$DIGEST_DATE"
      - name: Commit generated files
        run: |
          git add "${DIGEST_DATE:0:4}"
          git add -f data/runs data/state
          git pull --rebase --autostash origin main
          git push
""".strip(),
        encoding="utf-8",
    )


def _write_docs(root: Path) -> None:
    (root / "README.md").write_text(
        "CSTCLOUD_API_KEY\nWOS_API_KEY\nscripts/validate_daily.py\n",
        encoding="utf-8",
    )
    docs = root / "docs" / "operations.md"
    docs.parent.mkdir(parents=True)
    docs.write_text(
        "CSTCLOUD_API_KEY\nWOS_API_KEY\ndata/state/seen_dois.json\n",
        encoding="utf-8",
    )


def _write_valid_artifacts(root: Path, digest_date: str = "2026-05-28") -> None:
    run = root / "data" / "runs" / f"{digest_date}.json"
    run.parent.mkdir(parents=True)
    run.write_text(
        json.dumps(
            {
                "date": digest_date,
                "stages": {
                    "fetch_total": {"total": 100},
                    "keyword_score": {"above_threshold": 20},
                    "llm_relevance": {"candidates": 12, "kept": 8},
                    "build_digest": {"items": 8, "sections": 3, "highlights": 3},
                    "llm_grounding": {"passed": 8, "failed": 0, "errored": 0},
                    "output": {
                        "zh": f"2026/05/ecobio_digest_1d_{digest_date}_zh.md",
                        "en": f"2026/05/ecobio_digest_1d_{digest_date}_en.md",
                    },
                },
            }
        ),
        encoding="utf-8",
    )
    references = "\n".join(
        f"- **Paper {index}** — [Source](https://example.org/{index})"
        for index in range(8)
    )
    for lang in ("zh", "en"):
        path = root / "2026" / "05" / f"ecobio_digest_1d_{digest_date}_{lang}.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            f"# EcoBio Daily\n\n## Highlights\n\n- item\n\n## References\n\n{references}\n",
            encoding="utf-8",
        )
    state = root / "data" / "state" / "seen_dois.json"
    state.parent.mkdir(parents=True)
    state.write_text(json.dumps({"10.1234/example": digest_date}), encoding="utf-8")


def test_check_operations_accepts_ready_repository(tmp_path: Path):
    _write_workflow(tmp_path)
    _write_docs(tmp_path)
    _write_valid_artifacts(tmp_path)

    results = check_operations(tmp_path, digest_date="2026-05-28", since="2026-05-28")

    assert all(result.ok for result in results)
    assert {result.name for result in results} == {
        "daily workflow",
        "secret documentation",
        "daily artifacts",
        "run history",
    }


def test_check_operations_rejects_workflow_without_required_llm(tmp_path: Path):
    _write_workflow(tmp_path)
    _write_docs(tmp_path)
    _write_valid_artifacts(tmp_path)
    workflow = tmp_path / ".github" / "workflows" / "daily.yml"
    workflow.write_text(workflow.read_text(encoding="utf-8").replace(" --require-llm", ""), encoding="utf-8")

    results = check_operations(tmp_path, digest_date="2026-05-28", since="2026-05-28")

    assert any(not result.ok and "--require-llm" in result.detail for result in results)


def test_check_operations_rejects_node20_action_versions(tmp_path: Path):
    _write_workflow(tmp_path)
    _write_docs(tmp_path)
    _write_valid_artifacts(tmp_path)
    workflow = tmp_path / ".github" / "workflows" / "daily.yml"
    workflow.write_text(
        workflow.read_text(encoding="utf-8")
        .replace("actions/checkout@v6", "actions/checkout@v4")
        .replace("actions/setup-python@v6", "actions/setup-python@v5"),
        encoding="utf-8",
    )

    results = check_operations(tmp_path, digest_date="2026-05-28", since="2026-05-28")

    assert any(not result.ok and "Node 24 compatible" in result.detail for result in results)


def test_check_operations_rejects_bad_daily_artifacts(tmp_path: Path):
    _write_workflow(tmp_path)
    _write_docs(tmp_path)
    _write_valid_artifacts(tmp_path)
    (tmp_path / "data" / "state" / "seen_dois.json").unlink()

    results = check_operations(tmp_path, digest_date="2026-05-28", since="2026-05-28")

    assert any(not result.ok and "missing seen DOI state" in result.detail for result in results)
