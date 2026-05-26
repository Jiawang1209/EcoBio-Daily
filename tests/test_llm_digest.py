from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import httpx

from ecobio_daily.config import load_llm_config
from ecobio_daily.llm import LLMClient
from ecobio_daily.llm_digest import generate_section
from ecobio_daily.models import ScoredItem, SourceItem


def _make_config(tmp_path: Path):
    path = tmp_path / "llm.yaml"
    path.write_text(
        """
llm:
  enabled: true
  active_profile: v32
  profiles:
    v32:
      provider: openai_compatible
      base_url: https://example.com/v1
      model: deepseek-v3.2
      api_key_env: K
      temperature: 0.2
      max_tokens: 4000
      timeout_seconds: 90
  routing:
    digest_generation: v32
""".strip(),
        encoding="utf-8",
    )
    return load_llm_config(path)


def _capturing_client(
    tmp_path: Path,
    response_text: str | None = None,
    status: int = 200,
) -> tuple[LLMClient, dict]:
    captured: dict = {}

    def handler(req: httpx.Request) -> httpx.Response:
        body = json.loads(req.content.decode("utf-8"))
        captured["messages"] = body["messages"]
        captured["response_format"] = body.get("response_format")
        if status != 200:
            return httpx.Response(status, json={"error": "boom"})
        return httpx.Response(
            200,
            json={
                "id": "x",
                "object": "chat.completion",
                "model": "deepseek-v3.2",
                "choices": [
                    {
                        "index": 0,
                        "message": {"role": "assistant", "content": response_text},
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
    return (
        LLMClient(config=cfg, http_client=http_client, env={"K": "sk-test"}),
        captured,
    )


def _scored(title: str, summary: str = "Field measurements...") -> ScoredItem:
    item = SourceItem(
        id=title,
        title=title,
        url=f"https://example.org/{title.replace(' ', '-').lower()}",
        source="test",
        published_at=datetime(2026, 5, 27, tzinfo=timezone.utc),
        summary=summary,
    )
    return ScoredItem(item=item, relevance_score=5, topic_scores=[], llm_score=8)


_HAPPY_PATH_JSON = json.dumps(
    {
        "section_title": "土壤微生物简报",
        "highlights": ["要点1", "要点2", "要点3"],
        "items": [
            {
                "title": "Nitrogen fixation by diazotrophs in boreal forest soils",
                "summary_zh": "北方森林土壤中的固氮菌活性显著。",
                "why_it_matters": "为氮循环提供新机制。",
                "evidence_type": "实验",
                "caveat": "样本范围有限。",
                "source_url": "https://x",
            }
        ],
    },
    ensure_ascii=False,
)


def test_generate_section_returns_dict_with_required_fields(tmp_path: Path):
    client, _ = _capturing_client(tmp_path, response_text=_HAPPY_PATH_JSON)
    items = [_scored("Nitrogen fixation by diazotrophs in boreal forest soils")]

    result = generate_section("土壤微生物", items, client)

    assert result is not None
    assert result["section_title"] == "土壤微生物简报"
    assert len(result["highlights"]) == 3
    assert result["items"][0]["summary_zh"] == "北方森林土壤中的固氮菌活性显著。"


def test_generate_section_returns_none_on_invalid_json(tmp_path: Path):
    client, _ = _capturing_client(tmp_path, response_text="this is not json")
    items = [_scored("any title")]

    assert generate_section("土壤微生物", items, client) is None


def test_generate_section_returns_none_on_http_error(tmp_path: Path):
    client, _ = _capturing_client(tmp_path, status=500)
    items = [_scored("any title")]

    assert generate_section("土壤微生物", items, client) is None


def test_generate_section_prompt_contains_all_item_titles(tmp_path: Path):
    client, captured = _capturing_client(tmp_path, response_text=_HAPPY_PATH_JSON)
    items = [
        _scored("Forest soil nitrogen cycling paper"),
        _scored("Cropland methane oxidation paper"),
        _scored("Grassland grazing microbiome paper"),
    ]

    generate_section("土壤微生物", items, client)

    user_message = next(
        m["content"] for m in captured["messages"] if m["role"] == "user"
    )
    assert "Forest soil nitrogen cycling paper" in user_message
    assert "Cropland methane oxidation paper" in user_message
    assert "Grassland grazing microbiome paper" in user_message


def test_generate_section_prompt_contains_topic_name(tmp_path: Path):
    client, captured = _capturing_client(tmp_path, response_text=_HAPPY_PATH_JSON)
    items = [_scored("any title")]

    generate_section("草地土壤微生物", items, client)

    full_prompt = " ".join(m["content"] for m in captured["messages"])
    assert "草地土壤微生物" in full_prompt


def test_generate_section_requests_json_response_format(tmp_path: Path):
    client, captured = _capturing_client(tmp_path, response_text=_HAPPY_PATH_JSON)
    items = [_scored("any title")]

    generate_section("topic", items, client)

    assert captured["response_format"] == {"type": "json_object"}
