from pathlib import Path

import yaml


def test_daily_workflow_commits_run_metrics_and_seen_state():
    workflow = yaml.safe_load(Path(".github/workflows/daily.yml").read_text())
    commit_step = next(
        step for step in workflow["jobs"]["generate"]["steps"]
        if step["name"] == "Commit generated files"
    )

    assert "data/runs" in commit_step["run"]
    assert "data/state" in commit_step["run"]
    assert "git add -f data/runs data/state" in commit_step["run"]


def test_daily_workflow_documents_cstcloud_secret():
    workflow_text = Path(".github/workflows/daily.yml").read_text()

    assert "CSTCLOUD_API_KEY" in workflow_text
