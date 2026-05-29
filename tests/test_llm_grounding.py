from __future__ import annotations

import json
from pathlib import Path

import httpx

from ecobio_daily.config import load_llm_config
from ecobio_daily.llm import LLMClient
from ecobio_daily.llm_grounding import check_groundedness


def _make_config(tmp_path: Path):
    path = tmp_path / "llm.yaml"
    path.write_text(
        """
llm:
  enabled: true
  active_profile: flash
  profiles:
    flash:
      provider: openai_compatible
      base_url: https://example.com/v1
      model: deepseek-v4-flash
      api_key_env: K
      temperature: 0.1
      max_tokens: 300
      timeout_seconds: 30
  routing:
    grounding_check: flash
""".strip(),
        encoding="utf-8",
    )
    return load_llm_config(path)


def _capturing_client(
    tmp_path: Path,
    response_text: str | None = None,
    response_texts: list[str | None] | None = None,
    status: int = 200,
) -> tuple[LLMClient, dict]:
    captured: dict = {"calls": 0}

    def handler(req: httpx.Request) -> httpx.Response:
        body = json.loads(req.content.decode("utf-8"))
        captured["messages"] = body["messages"]
        captured["calls"] += 1
        if status != 200:
            return httpx.Response(status, json={"error": "boom"})
        content = response_text
        if response_texts is not None:
            content = response_texts[min(captured["calls"] - 1, len(response_texts) - 1)]
        return httpx.Response(
            200,
            json={
                "id": "x",
                "object": "chat.completion",
                "model": "deepseek-v4-flash",
                "choices": [
                    {
                        "index": 0,
                        "message": {"role": "assistant", "content": content},
                        "finish_reason": "stop",
                    }
                ],
                "usage": {
                    "prompt_tokens": 1,
                    "completion_tokens": 1,
                    "total_tokens": 2,
                },
            },
        )

    transport = httpx.MockTransport(handler)
    http_client = httpx.Client(transport=transport)
    cfg = _make_config(tmp_path)
    client = LLMClient(
        config=cfg, http_client=http_client, env={"K": "sk-test"}
    )
    return client, captured


_BRIEF_ITEM = {
    "title": "Forest paper",
    "title_zh": "森林论文",
    "summary_zh": "中文摘要内容。",
    "why_it_matters": "重要性说明。",
    "evidence_type": "实验",
    "caveat": None,
    "source_url": "https://x",
}


def test_check_groundedness_returns_passing_verdict(tmp_path: Path):
    client, _ = _capturing_client(
        tmp_path,
        response_text='{"grounded": true, "score": 9, "reason": "完全对应"}',
    )

    result = check_groundedness("English abstract here.", _BRIEF_ITEM, client)

    assert result == {"grounded": True, "score": 9, "reason": "完全对应"}


def test_check_groundedness_returns_failing_verdict(tmp_path: Path):
    client, _ = _capturing_client(
        tmp_path,
        response_text='{"grounded": false, "score": 3, "reason": "数字未对应"}',
    )

    result = check_groundedness("English abstract here.", _BRIEF_ITEM, client)

    assert result == {"grounded": False, "score": 3, "reason": "数字未对应"}


def test_check_groundedness_returns_none_on_invalid_json(tmp_path: Path):
    client, _ = _capturing_client(tmp_path, response_text="not json at all")

    assert check_groundedness("abstract", _BRIEF_ITEM, client) is None


def test_check_groundedness_retries_once_after_invalid_json(tmp_path: Path):
    client, captured = _capturing_client(
        tmp_path,
        response_texts=[
            "not json at all",
            '{"grounded": true, "score": 9, "reason": "retry ok"}',
        ],
    )

    result = check_groundedness("abstract", _BRIEF_ITEM, client)

    assert result == {"grounded": True, "score": 9, "reason": "retry ok"}
    assert captured["calls"] == 2


def test_check_groundedness_returns_none_on_http_error(tmp_path: Path):
    client, _ = _capturing_client(tmp_path, status=500)

    assert check_groundedness("abstract", _BRIEF_ITEM, client) is None


def test_check_groundedness_prompt_includes_abstract_and_summary(tmp_path: Path):
    client, captured = _capturing_client(
        tmp_path,
        response_text='{"grounded": true, "score": 9, "reason": "ok"}',
    )

    check_groundedness(
        "The forest soil paper specifically mentions diazotrophs.",
        _BRIEF_ITEM,
        client,
    )

    full_prompt = " ".join(m["content"] for m in captured["messages"])
    assert "diazotrophs" in full_prompt
    assert "中文摘要内容" in full_prompt
    assert "重要性说明" in full_prompt


def test_check_groundedness_strips_code_fence(tmp_path: Path):
    wrapped = '```json\n{"grounded": true, "score": 9, "reason": "ok"}\n```'
    client, _ = _capturing_client(tmp_path, response_text=wrapped)

    result = check_groundedness("abstract", _BRIEF_ITEM, client)

    assert result is not None
    assert result["grounded"] is True
