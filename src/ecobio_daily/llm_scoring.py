from __future__ import annotations

import json
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from ecobio_daily.llm import LLMClient, LLMError
from ecobio_daily.models import SourceItem


_PROMPT_DIR = Path(__file__).resolve().parents[2] / "templates" / "prompts"
_PROMPT_NAME = "relevance_score.md.j2"


def _render_prompt(item: SourceItem) -> str:
    env = Environment(
        loader=FileSystemLoader(str(_PROMPT_DIR)),
        autoescape=False,
        keep_trailing_newline=True,
    )
    template = env.get_template(_PROMPT_NAME)
    return template.render(item=item)


def score_relevance(item: SourceItem, client: LLMClient) -> int:
    prompt = _render_prompt(item)
    try:
        response = client.chat(
            messages=[{"role": "user", "content": prompt}],
            task="relevance_scoring",
            response_format="json_object",
        )
    except LLMError:
        return -1

    try:
        data = json.loads(response)
        score = int(data["score"])
    except (json.JSONDecodeError, KeyError, TypeError, ValueError):
        return -1

    if not 0 <= score <= 10:
        return -1
    return score


def batch_score(items: list[SourceItem], client: LLMClient) -> list[int]:
    return [score_relevance(item, client) for item in items]
