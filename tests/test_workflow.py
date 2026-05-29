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
    assert "$DIGEST_DATE" in commit_step["run"]


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
    assert "$DIGEST_DATE" in generate_step["run"]


def test_daily_workflow_passes_optional_wos_secret_to_generation():
    workflow = yaml.safe_load(Path(".github/workflows/daily.yml").read_text())
    generate_step = next(
        step for step in workflow["jobs"]["generate"]["steps"]
        if step["name"] == "Generate digest"
    )

    assert generate_step["env"]["WOS_API_KEY"] == "${{ secrets.WOS_API_KEY }}"


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


def test_daily_workflow_validates_digest_before_commit():
    workflow = yaml.safe_load(Path(".github/workflows/daily.yml").read_text())
    steps = workflow["jobs"]["generate"]["steps"]
    validate_index = next(
        index for index, step in enumerate(steps)
        if step["name"] == "Validate generated digest"
    )
    commit_index = next(
        index for index, step in enumerate(steps)
        if step["name"] == "Commit generated files"
    )
    validate_step = steps[validate_index]

    assert validate_index < commit_index
    assert "scripts/validate_daily.py" in validate_step["run"]
    assert "$DIGEST_DATE" in validate_step["run"]


def test_daily_workflow_writes_github_step_summary_after_validation():
    workflow = yaml.safe_load(Path(".github/workflows/daily.yml").read_text())
    steps = workflow["jobs"]["generate"]["steps"]
    validate_index = next(
        index for index, step in enumerate(steps)
        if step["name"] == "Validate generated digest"
    )
    summary_index = next(
        index for index, step in enumerate(steps)
        if step["name"] == "Write run summary"
    )
    commit_index = next(
        index for index, step in enumerate(steps)
        if step["name"] == "Commit generated files"
    )
    summary_step = steps[summary_index]

    assert validate_index < summary_index < commit_index
    assert "GITHUB_STEP_SUMMARY" in summary_step["run"]
    assert "data/runs/" in summary_step["run"]
    assert "DIGEST_DATE" in summary_step["run"]
    assert "build_digest" in summary_step["run"]
    assert "llm_grounding" in summary_step["run"]


def test_daily_workflow_supports_manual_digest_date_input():
    workflow = yaml.safe_load(Path(".github/workflows/daily.yml").read_text())

    dispatch = workflow[True]["workflow_dispatch"]
    assert "digest_date" in dispatch["inputs"]
    assert dispatch["inputs"]["digest_date"]["required"] is False


def test_daily_workflow_resolves_digest_date_once_before_generation():
    workflow = yaml.safe_load(Path(".github/workflows/daily.yml").read_text())
    steps = workflow["jobs"]["generate"]["steps"]
    resolve_index = next(
        index for index, step in enumerate(steps)
        if step["name"] == "Resolve digest date"
    )
    generate_index = next(
        index for index, step in enumerate(steps)
        if step["name"] == "Generate digest"
    )
    resolve_step = steps[resolve_index]

    assert resolve_index < generate_index
    assert "GITHUB_ENV" in resolve_step["run"]
    assert "DIGEST_DATE" in resolve_step["run"]


def test_daily_workflow_serializes_runs_to_protect_state_files():
    workflow = yaml.safe_load(Path(".github/workflows/daily.yml").read_text())

    assert workflow["concurrency"]["group"] == "ecobio-daily"
    assert workflow["concurrency"]["cancel-in-progress"] is False


def test_daily_workflow_avoids_top_of_hour_schedule_drop_risk():
    workflow = yaml.safe_load(Path(".github/workflows/daily.yml").read_text())

    schedules = workflow[True]["schedule"]

    assert schedules == [{"cron": "17 0 * * *"}]


def test_daily_workflow_rebases_before_push_to_avoid_stale_checkout():
    workflow = yaml.safe_load(Path(".github/workflows/daily.yml").read_text())
    commit_step = next(
        step for step in workflow["jobs"]["generate"]["steps"]
        if step["name"] == "Commit generated files"
    )
    run = commit_step["run"]

    assert "git pull --rebase --autostash origin main" in run
    assert run.index("git pull --rebase --autostash origin main") < run.index("git push")


def test_ci_workflow_runs_pytest_on_push_and_pull_request():
    workflow = yaml.safe_load(Path(".github/workflows/ci.yml").read_text())

    assert "push" in workflow[True]
    assert "pull_request" in workflow[True]
    steps = workflow["jobs"]["tests"]["steps"]
    assert any(step.get("uses") == "actions/setup-python@v6" for step in steps)
    assert any("python -m pip install -e \".[dev]\"" in step.get("run", "") for step in steps)
    assert any("python -m pytest -q" in step.get("run", "") for step in steps)


def test_workflows_use_node24_compatible_official_actions():
    workflow_paths = [
        Path(".github/workflows/ci.yml"),
        Path(".github/workflows/daily.yml"),
    ]

    for path in workflow_paths:
        workflow = yaml.safe_load(path.read_text())
        for job in workflow["jobs"].values():
            for step in job["steps"]:
                assert step.get("uses") != "actions/checkout@v4", path
                assert step.get("uses") != "actions/setup-python@v5", path
                if step.get("name") == "Check out repository":
                    assert step["uses"] == "actions/checkout@v6"
                if step.get("name") == "Set up Python":
                    assert step["uses"] == "actions/setup-python@v6"
