from pathlib import Path

import pytest

from scripts.summarize_runs import filter_run_summaries, load_run_summaries, validate_run_history


def _write_run(
    root: Path,
    digest_date: str,
    items: int,
    grounding_failed: int = 0,
    grounding_errored: int = 0,
    grounding_repaired: int = 0,
) -> None:
    path = root / "data" / "runs" / f"{digest_date}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        f"""{{
  "date": "{digest_date}",
  "duration_seconds": 12.3,
  "stages": {{
    "fetch_total": {{"total": 100}},
    "keyword_score": {{"above_threshold": 20}},
    "llm_relevance": {{"candidates": 12, "kept": 8, "backfilled": 1}},
    "build_digest": {{"items": {items}, "sections": 3, "highlights": 3}},
    "llm_grounding": {{"passed": {items - grounding_failed}, "failed": {grounding_failed}, "errored": {grounding_errored}, "repaired": {grounding_repaired}}}
  }}
}}""",
        encoding="utf-8",
    )


def test_load_run_summaries_returns_sorted_summary_rows(tmp_path: Path):
    _write_run(tmp_path, "2026-05-28", items=8)
    _write_run(tmp_path, "2026-05-27", items=3)

    rows = load_run_summaries(tmp_path)

    assert [row["date"] for row in rows] == ["2026-05-27", "2026-05-28"]
    assert rows[1]["items"] == 8
    assert rows[1]["llm_kept"] == 8
    assert rows[1]["grounding_failed"] == 0


def test_load_run_summaries_includes_grounding_repair_count(tmp_path: Path):
    _write_run(tmp_path, "2026-05-28", items=8, grounding_repaired=1)

    rows = load_run_summaries(tmp_path)

    assert rows[0]["grounding_repaired"] == 1


def test_validate_run_history_can_ignore_runs_before_start_date(tmp_path: Path):
    _write_run(tmp_path, "2026-05-27", items=3)
    _write_run(tmp_path, "2026-05-28", items=8)

    validate_run_history(tmp_path, since="2026-05-28")


def test_filter_run_summaries_returns_only_rows_on_or_after_start_date(tmp_path: Path):
    _write_run(tmp_path, "2026-05-27", items=3, grounding_failed=1)
    _write_run(tmp_path, "2026-05-28", items=8)

    rows = filter_run_summaries(load_run_summaries(tmp_path), since="2026-05-28")

    assert [row["date"] for row in rows] == ["2026-05-28"]


def test_validate_run_history_rejects_bad_item_count_after_start_date(tmp_path: Path):
    _write_run(tmp_path, "2026-05-28", items=4)

    with pytest.raises(SystemExit, match="expected 5-8 items"):
        validate_run_history(tmp_path, since="2026-05-28")


def test_validate_run_history_rejects_grounding_failures(tmp_path: Path):
    _write_run(tmp_path, "2026-05-28", items=8, grounding_failed=1)

    with pytest.raises(SystemExit, match="grounding failures"):
        validate_run_history(tmp_path, since="2026-05-28")


def test_validate_run_history_accepts_grounding_errors_that_were_repaired(tmp_path: Path):
    _write_run(tmp_path, "2026-05-28", items=8, grounding_errored=1, grounding_repaired=1)

    validate_run_history(tmp_path, since="2026-05-28")
