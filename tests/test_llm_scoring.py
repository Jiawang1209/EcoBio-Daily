from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import httpx

from ecobio_daily.config import load_llm_config
from ecobio_daily.llm import LLMClient
from ecobio_daily.llm_scoring import batch_score, score_relevance
from ecobio_daily.models import SourceItem


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
      temperature: 0.2
      max_tokens: 200
      timeout_seconds: 30
  routing:
    relevance_scoring: flash
""".strip(),
        encoding="utf-8",
    )
    return load_llm_config(path)


def _mock_client(
    tmp_path: Path,
    response_text: str | None = None,
    status: int = 200,
) -> LLMClient:
    def handler(req: httpx.Request) -> httpx.Response:
        if status != 200:
            return httpx.Response(status, json={"error": "boom"})
        return httpx.Response(
            200,
            json={
                "id": "x",
                "object": "chat.completion",
                "model": "deepseek-v4-flash",
                "choices": [
                    {
                        "index": 0,
                        "message": {
                            "role": "assistant",
                            "content": response_text,
                        },
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
    return LLMClient(config=cfg, http_client=http_client, env={"K": "test-key"})


def _make_item(title: str, summary: str = "") -> SourceItem:
    return SourceItem(
        id="t",
        title=title,
        url="https://x",
        source="t",
        published_at=datetime(2026, 5, 26, tzinfo=timezone.utc),
        summary=summary,
    )


def test_score_relevance_high_for_soil_paper(tmp_path: Path):
    client = _mock_client(
        tmp_path, response_text='{"score": 9, "reason": "森林固氮核心命中"}'
    )
    item = _make_item(
        "Nitrogen fixation by free-living diazotrophs in boreal forest soils"
    )
    assert score_relevance(item, client) == 9


def test_score_relevance_low_for_clinical_paper(tmp_path: Path):
    client = _mock_client(
        tmp_path, response_text='{"score": 1, "reason": "宿主临床排除"}'
    )
    item = _make_item("Gut microbiome composition predicts diabetes outcomes")
    assert score_relevance(item, client) == 1


def test_score_relevance_returns_minus_one_on_invalid_json(tmp_path: Path):
    client = _mock_client(tmp_path, response_text="not a json at all")
    item = _make_item("Anything")
    assert score_relevance(item, client) == -1


def test_score_relevance_returns_minus_one_on_http_error(tmp_path: Path):
    client = _mock_client(tmp_path, status=500)
    item = _make_item("Anything")
    assert score_relevance(item, client) == -1


def test_score_relevance_returns_minus_one_on_out_of_range_score(tmp_path: Path):
    client = _mock_client(
        tmp_path, response_text='{"score": 42, "reason": "x"}'
    )
    item = _make_item("Anything")
    assert score_relevance(item, client) == -1


def test_batch_score_returns_one_score_per_item(tmp_path: Path):
    client = _mock_client(tmp_path, response_text='{"score": 7, "reason": "ok"}')
    items = [_make_item("a"), _make_item("b"), _make_item("c")]
    assert batch_score(items, client) == [7, 7, 7]
