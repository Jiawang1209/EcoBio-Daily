from pathlib import Path
import json

import pytest

from scripts.validate_daily import validate_daily


def _write_metrics(
    root: Path,
    digest_date: str = "2026-05-28",
    items: int = 8,
    grounding_failed: int = 0,
    grounding_errored: int = 0,
) -> None:
    path = root / "data" / "runs" / f"{digest_date}.json"
    path.parent.mkdir(parents=True)
    path.write_text(
        f"""{{
  "date": "{digest_date}",
  "stages": {{
    "build_digest": {{"items": {items}}},
    "llm_grounding": {{"failed": {grounding_failed}, "errored": {grounding_errored}}},
    "output": {{
      "zh": "2026/05/ecobio_digest_1d_{digest_date}_zh.md",
      "en": "2026/05/ecobio_digest_1d_{digest_date}_en.md"
    }}
  }}
}}""",
        encoding="utf-8",
    )
    zh = root / "2026" / "05" / f"ecobio_digest_1d_{digest_date}_zh.md"
    en = root / "2026" / "05" / f"ecobio_digest_1d_{digest_date}_en.md"
    zh.parent.mkdir(parents=True)
    references = "\n".join(f"- **Paper {index}** — [Source](https://example.org/{index})" for index in range(items))
    zh.write_text(
        f"# zh\n\n## Highlights\n\n- **A**：summary\n\n## Section\n\n### A\n\nBody\n\n## References\n\n{references}\n",
        encoding="utf-8",
    )
    en.write_text(
        f"# en\n\n## Highlights\n\n- **A**: summary\n\n## Section\n\n### A\n\nBody\n\n## References\n\n{references}\n",
        encoding="utf-8",
    )
    state = root / "data" / "state" / "seen_dois.json"
    state.parent.mkdir(parents=True)
    state.write_text(
        json.dumps({"10.1234/example": digest_date}, ensure_ascii=False),
        encoding="utf-8",
    )


def test_validate_daily_accepts_good_metrics(tmp_path: Path):
    _write_metrics(tmp_path)

    validate_daily(tmp_path, "2026-05-28")


def test_validate_daily_rejects_too_few_items(tmp_path: Path):
    _write_metrics(tmp_path, items=4)

    with pytest.raises(SystemExit, match="expected 5-8 digest items"):
        validate_daily(tmp_path, "2026-05-28")


def test_validate_daily_rejects_grounding_failures(tmp_path: Path):
    _write_metrics(tmp_path, grounding_failed=1)

    with pytest.raises(SystemExit, match="grounding check failed"):
        validate_daily(tmp_path, "2026-05-28")


def test_validate_daily_rejects_missing_output_file(tmp_path: Path):
    _write_metrics(tmp_path)
    (tmp_path / "2026/05/ecobio_digest_1d_2026-05-28_en.md").unlink()

    with pytest.raises(SystemExit, match="missing output file"):
        validate_daily(tmp_path, "2026-05-28")


def test_validate_daily_rejects_output_missing_references_section(tmp_path: Path):
    _write_metrics(tmp_path)
    (tmp_path / "2026/05/ecobio_digest_1d_2026-05-28_zh.md").write_text(
        "# zh\n\n## Highlights\n\n- **A**：summary\n",
        encoding="utf-8",
    )

    with pytest.raises(SystemExit, match="missing References section"):
        validate_daily(tmp_path, "2026-05-28")


def test_validate_daily_rejects_output_with_too_few_reference_items(tmp_path: Path):
    _write_metrics(tmp_path, items=8)
    (tmp_path / "2026/05/ecobio_digest_1d_2026-05-28_en.md").write_text(
        "# en\n\n## Highlights\n\n- **A**: summary\n\n## References\n\n- **Only one** — [Source](https://example.org/1)\n",
        encoding="utf-8",
    )

    with pytest.raises(SystemExit, match="expected at least 8 references"):
        validate_daily(tmp_path, "2026-05-28")


def test_validate_daily_rejects_missing_seen_state(tmp_path: Path):
    _write_metrics(tmp_path)
    (tmp_path / "data/state/seen_dois.json").unlink()

    with pytest.raises(SystemExit, match="missing seen DOI state"):
        validate_daily(tmp_path, "2026-05-28")


def test_validate_daily_rejects_invalid_seen_state_json(tmp_path: Path):
    _write_metrics(tmp_path)
    (tmp_path / "data/state/seen_dois.json").write_text("{bad json", encoding="utf-8")

    with pytest.raises(SystemExit, match="invalid seen DOI state JSON"):
        validate_daily(tmp_path, "2026-05-28")
