from __future__ import annotations

import json
from datetime import date
from pathlib import Path

from ecobio_daily.run_metrics import RunMetrics


def test_record_stores_stage_under_named_key():
    m = RunMetrics(digest_date=date(2026, 5, 27))
    m.record("url_dedup", in_count=150, out_count=120)

    assert m.stages["url_dedup"] == {"in_count": 150, "out_count": 120}


def test_record_overwrites_when_same_stage_called_twice():
    m = RunMetrics(digest_date=date(2026, 5, 27))
    m.record("llm_brief", ok=2, failed=0)
    m.record("llm_brief", ok=3, failed=1)

    assert m.stages["llm_brief"] == {"ok": 3, "failed": 1}


def test_save_writes_json_with_date_and_stages(tmp_path: Path):
    m = RunMetrics(digest_date=date(2026, 5, 27))
    m.record("url_dedup", in_count=150, out_count=120)
    m.finalize()
    out = tmp_path / "runs" / "2026-05-27.json"

    m.save(out)

    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["date"] == "2026-05-27"
    assert data["stages"]["url_dedup"] == {"in_count": 150, "out_count": 120}
    assert data["duration_seconds"] >= 0
    assert "started_at" in data and "completed_at" in data


def test_save_creates_parent_directory(tmp_path: Path):
    m = RunMetrics(digest_date=date(2026, 5, 27))
    m.finalize()
    out = tmp_path / "deeply" / "nested" / "runs" / "x.json"

    m.save(out)

    assert out.exists()
