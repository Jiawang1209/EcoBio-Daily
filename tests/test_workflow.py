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


def test_daily_workflow_requires_llm_secret_for_ci_quality():
    workflow = yaml.safe_load(Path(".github/workflows/daily.yml").read_text())
    generate_step = next(
        step for step in workflow["jobs"]["generate"]["steps"]
        if step["name"] == "Generate digest"
    )

    assert "--require-llm" in generate_step["run"]


def test_daily_workflow_validates_cstcloud_secret_before_generation():
    workflow = yaml.safe_load(Path(".github/workflows/daily.yml").read_text())
    steps = workflow["jobs"]["generate"]["steps"]
    validate_index = next(
        index for index, step in enumerate(steps)
        if step["name"] == "Validate LLM secret"
    )
    generate_index = next(
        index for index, step in enumerate(steps)
        if step["name"] == "Generate digest"
    )
    validate_step = steps[validate_index]

    assert validate_index < generate_index
    assert "CSTCLOUD_API_KEY" in validate_step["env"]
    assert "CSTCLOUD_API_KEY secret is not configured" in validate_step["run"]
