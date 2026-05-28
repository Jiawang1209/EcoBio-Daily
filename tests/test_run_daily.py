from pathlib import Path

import pytest

from scripts.run_daily import _maybe_build_llm_client


def _write_llm_config(path: Path, enabled: bool = True) -> None:
    path.write_text(
        f"""
llm:
  enabled: {str(enabled).lower()}
  active_profile: p1
  profiles:
    p1:
      provider: openai_compatible
      base_url: https://example.com/v1
      model: test-model
      api_key_env: CSTCLOUD_API_KEY
  routing:
    relevance_scoring: p1
  budget:
    cache_llm_outputs: false
""".strip(),
        encoding="utf-8",
    )


def test_maybe_build_llm_client_returns_none_when_disabled(tmp_path: Path):
    config = tmp_path / "llm.yaml"
    _write_llm_config(config, enabled=False)

    assert _maybe_build_llm_client(config, tmp_path / ".env", require_llm=False) is None


def test_maybe_build_llm_client_fails_when_required_key_missing(
    tmp_path: Path, monkeypatch
):
    config = tmp_path / "llm.yaml"
    _write_llm_config(config)
    monkeypatch.delenv("CSTCLOUD_API_KEY", raising=False)

    with pytest.raises(RuntimeError, match="CSTCLOUD_API_KEY"):
        _maybe_build_llm_client(config, tmp_path / ".env", require_llm=True)


def test_maybe_build_llm_client_uses_dotenv_when_required(tmp_path: Path, monkeypatch):
    config = tmp_path / "llm.yaml"
    dotenv = tmp_path / ".env"
    _write_llm_config(config)
    dotenv.write_text("CSTCLOUD_API_KEY=sk-test\n", encoding="utf-8")
    monkeypatch.delenv("CSTCLOUD_API_KEY", raising=False)

    client = _maybe_build_llm_client(config, dotenv, require_llm=True)

    assert client is not None
