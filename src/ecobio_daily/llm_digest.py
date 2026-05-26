from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader

from ecobio_daily.llm import LLMClient, LLMError
from ecobio_daily.models import ScoredItem


_PROMPT_DIR = Path(__file__).resolve().parents[2] / "templates" / "prompts"
_SYSTEM_TEMPLATE = "digest_section_zh_system.md.j2"
_USER_TEMPLATE = "digest_section_zh_user.md.j2"


def _render(template_name: str, **context: Any) -> str:
    env = Environment(
        loader=FileSystemLoader(str(_PROMPT_DIR)),
        autoescape=False,
        keep_trailing_newline=True,
    )
    template = env.get_template(template_name)
    return template.render(**context)


def generate_section(
    topic_name: str,
    items: list[ScoredItem],
    client: LLMClient,
) -> dict | None:
    system = _render(_SYSTEM_TEMPLATE)
    user = _render(_USER_TEMPLATE, topic_name=topic_name, items=items)

    try:
        response = client.chat(
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            task="digest_generation",
            response_format="json_object",
        )
    except LLMError:
        return None

    try:
        result = json.loads(_strip_code_fence(response))
    except json.JSONDecodeError:
        return None
    if not isinstance(result, dict):
        return None
    return result


def _strip_code_fence(text: str) -> str:
    stripped = text.strip()
    if not stripped.startswith("```"):
        return stripped
    first_newline = stripped.find("\n")
    if first_newline == -1:
        return stripped
    inner = stripped[first_newline + 1 :]
    if inner.endswith("```"):
        inner = inner[:-3]
    return inner.strip()
