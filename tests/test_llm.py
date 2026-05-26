from __future__ import annotations

from pathlib import Path

import httpx
import pytest

from ecobio_daily.config import load_llm_config
from ecobio_daily.llm import (
    LLMClient,
    LLMMissingKeyError,
    LLMRequestError,
    load_dotenv,
)


# ---------- load_llm_config ----------


def test_load_llm_config_allows_null_routing_entries(tmp_path: Path):
    path = tmp_path / "llm.yaml"
    path.write_text(
        """
llm:
  enabled: true
  active_profile: p1
  profiles:
    p1:
      provider: openai_compatible
      base_url: https://example.com/v1
      model: m1
      api_key_env: K
  routing:
    relevance_scoring: p1
    final_polish: null
""".strip(),
        encoding="utf-8",
    )

    cfg = load_llm_config(path)

    assert cfg.routing["relevance_scoring"] == "p1"
    assert cfg.routing["final_polish"] is None


def test_load_llm_config_parses_profiles_and_routing(tmp_path: Path):
    path = tmp_path / "llm.yaml"
    path.write_text(
        """
llm:
  enabled: true
  active_profile: cstcloud_flash
  profiles:
    cstcloud_flash:
      provider: openai_compatible
      base_url: https://uni-api.cstcloud.cn/v1
      model: deepseek-v4-flash
      api_key_env: CSTCLOUD_API_KEY
      temperature: 0.2
      max_tokens: 1500
      timeout_seconds: 60
    cstcloud_v32:
      provider: openai_compatible
      base_url: https://uni-api.cstcloud.cn/v1
      model: deepseek-v3.2
      api_key_env: CSTCLOUD_API_KEY
      temperature: 0.2
      max_tokens: 4000
      timeout_seconds: 90
  routing:
    relevance_scoring: cstcloud_flash
    digest_generation: cstcloud_v32
""".strip(),
        encoding="utf-8",
    )

    cfg = load_llm_config(path)

    assert cfg.enabled is True
    assert cfg.active_profile == "cstcloud_flash"
    assert set(cfg.profiles.keys()) == {"cstcloud_flash", "cstcloud_v32"}
    assert cfg.profiles["cstcloud_flash"].model == "deepseek-v4-flash"
    assert cfg.profiles["cstcloud_flash"].api_key_env == "CSTCLOUD_API_KEY"
    assert cfg.routing["relevance_scoring"] == "cstcloud_flash"
    assert cfg.routing["digest_generation"] == "cstcloud_v32"


# ---------- load_dotenv ----------


def test_load_dotenv_parses_simple_key_value(tmp_path: Path):
    path = tmp_path / ".env"
    path.write_text("CSTCLOUD_API_KEY=sk-test-123\n", encoding="utf-8")

    env = load_dotenv(path)

    assert env == {"CSTCLOUD_API_KEY": "sk-test-123"}


def test_load_dotenv_ignores_comments_and_blanks(tmp_path: Path):
    path = tmp_path / ".env"
    path.write_text(
        """
# this is a comment
CSTCLOUD_API_KEY=sk-test-123

# another comment
OTHER_KEY=value with spaces
""",
        encoding="utf-8",
    )

    env = load_dotenv(path)

    assert env == {
        "CSTCLOUD_API_KEY": "sk-test-123",
        "OTHER_KEY": "value with spaces",
    }


def test_load_dotenv_returns_empty_when_file_missing(tmp_path: Path):
    env = load_dotenv(tmp_path / "does-not-exist.env")
    assert env == {}


# ---------- LLMClient.resolve_profile ----------


def _make_config(tmp_path: Path) -> "object":
    path = tmp_path / "llm.yaml"
    path.write_text(
        """
llm:
  enabled: true
  active_profile: cstcloud_flash
  profiles:
    cstcloud_flash:
      provider: openai_compatible
      base_url: https://uni-api.cstcloud.cn/v1
      model: deepseek-v4-flash
      api_key_env: CSTCLOUD_API_KEY
      temperature: 0.2
      max_tokens: 1500
      timeout_seconds: 60
    cstcloud_v32:
      provider: openai_compatible
      base_url: https://uni-api.cstcloud.cn/v1
      model: deepseek-v3.2
      api_key_env: CSTCLOUD_API_KEY
      temperature: 0.2
      max_tokens: 4000
      timeout_seconds: 90
  routing:
    relevance_scoring: cstcloud_flash
    digest_generation: cstcloud_v32
""".strip(),
        encoding="utf-8",
    )
    return load_llm_config(path)


def test_resolve_profile_by_explicit_name(tmp_path: Path):
    cfg = _make_config(tmp_path)
    client = LLMClient(config=cfg, env={"CSTCLOUD_API_KEY": "sk-test"})

    profile = client.resolve_profile(name="cstcloud_v32")

    assert profile.model == "deepseek-v3.2"


def test_resolve_profile_by_routing_task(tmp_path: Path):
    cfg = _make_config(tmp_path)
    client = LLMClient(config=cfg, env={"CSTCLOUD_API_KEY": "sk-test"})

    profile = client.resolve_profile(task="digest_generation")

    assert profile.model == "deepseek-v3.2"


def test_resolve_profile_falls_back_to_active_profile(tmp_path: Path):
    cfg = _make_config(tmp_path)
    client = LLMClient(config=cfg, env={"CSTCLOUD_API_KEY": "sk-test"})

    profile = client.resolve_profile()

    assert profile.model == "deepseek-v4-flash"  # active_profile


# ---------- LLMClient.chat ----------


def _mock_transport(captured: dict, response_payload: dict, status: int = 200):
    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["headers"] = dict(request.headers)
        import json

        captured["body"] = json.loads(request.content.decode("utf-8"))
        return httpx.Response(status, json=response_payload)

    return httpx.MockTransport(handler)


def _openai_style_response(text: str) -> dict:
    return {
        "id": "test-id",
        "object": "chat.completion",
        "model": "deepseek-v4-flash",
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": text},
                "finish_reason": "stop",
            }
        ],
        "usage": {"prompt_tokens": 5, "completion_tokens": 2, "total_tokens": 7},
    }


def test_chat_returns_message_content(tmp_path: Path):
    cfg = _make_config(tmp_path)
    captured: dict = {}
    transport = _mock_transport(captured, _openai_style_response("hello-zh"))
    http_client = httpx.Client(transport=transport)
    client = LLMClient(
        config=cfg,
        http_client=http_client,
        env={"CSTCLOUD_API_KEY": "sk-test"},
    )

    text = client.chat(messages=[{"role": "user", "content": "hi"}])

    assert text == "hello-zh"


def test_chat_builds_openai_compatible_payload(tmp_path: Path):
    cfg = _make_config(tmp_path)
    captured: dict = {}
    transport = _mock_transport(captured, _openai_style_response("ok"))
    http_client = httpx.Client(transport=transport)
    client = LLMClient(
        config=cfg,
        http_client=http_client,
        env={"CSTCLOUD_API_KEY": "sk-test-abc"},
    )

    client.chat(messages=[{"role": "user", "content": "hi"}])

    assert captured["url"] == "https://uni-api.cstcloud.cn/v1/chat/completions"
    assert captured["headers"]["authorization"] == "Bearer sk-test-abc"
    assert captured["headers"]["content-type"].startswith("application/json")
    assert captured["body"]["model"] == "deepseek-v4-flash"
    assert captured["body"]["messages"] == [{"role": "user", "content": "hi"}]
    assert captured["body"]["temperature"] == 0.2
    assert captured["body"]["max_tokens"] == 1500


def test_chat_supports_json_response_format(tmp_path: Path):
    cfg = _make_config(tmp_path)
    captured: dict = {}
    transport = _mock_transport(captured, _openai_style_response('{"a":1}'))
    http_client = httpx.Client(transport=transport)
    client = LLMClient(
        config=cfg,
        http_client=http_client,
        env={"CSTCLOUD_API_KEY": "sk-test"},
    )

    client.chat(
        messages=[{"role": "user", "content": "give json"}],
        response_format="json_object",
    )

    assert captured["body"]["response_format"] == {"type": "json_object"}


def test_chat_uses_profile_specified_by_task(tmp_path: Path):
    cfg = _make_config(tmp_path)
    captured: dict = {}
    transport = _mock_transport(captured, _openai_style_response("ok"))
    http_client = httpx.Client(transport=transport)
    client = LLMClient(
        config=cfg,
        http_client=http_client,
        env={"CSTCLOUD_API_KEY": "sk-test"},
    )

    client.chat(
        messages=[{"role": "user", "content": "hi"}],
        task="digest_generation",
    )

    assert captured["body"]["model"] == "deepseek-v3.2"
    assert captured["body"]["max_tokens"] == 4000


def test_chat_raises_when_api_key_missing(tmp_path: Path):
    cfg = _make_config(tmp_path)
    client = LLMClient(config=cfg, env={})  # no CSTCLOUD_API_KEY

    with pytest.raises(LLMMissingKeyError) as excinfo:
        client.chat(messages=[{"role": "user", "content": "hi"}])

    assert "CSTCLOUD_API_KEY" in str(excinfo.value)


def test_chat_raises_on_http_error(tmp_path: Path):
    cfg = _make_config(tmp_path)
    captured: dict = {}
    transport = _mock_transport(captured, {"error": "boom"}, status=500)
    http_client = httpx.Client(transport=transport)
    client = LLMClient(
        config=cfg,
        http_client=http_client,
        env={"CSTCLOUD_API_KEY": "sk-test"},
    )

    with pytest.raises(LLMRequestError) as excinfo:
        client.chat(messages=[{"role": "user", "content": "hi"}])

    assert "500" in str(excinfo.value)
