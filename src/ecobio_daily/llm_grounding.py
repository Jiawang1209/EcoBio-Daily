from __future__ import annotations

import json
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from ecobio_daily.llm import LLMClient, LLMError


_PROMPT_DIR = Path(__file__).resolve().parents[2] / "templates" / "prompts"
_TEMPLATE = "grounding_check.md.j2"


def _render_prompt(abstract: str, brief: dict) -> str:
    env = Environment(
        loader=FileSystemLoader(str(_PROMPT_DIR)),
        autoescape=False,
        keep_trailing_newline=True,
    )
    template = env.get_template(_TEMPLATE)
    return template.render(abstract=abstract, brief=brief)


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


def check_groundedness(
    abstract: str,
    brief_item: dict,
    client: LLMClient,
) -> dict | None:
    prompt = _render_prompt(abstract, brief_item)
    try:
        response = client.chat(
            messages=[{"role": "user", "content": prompt}],
            task="grounding_check",
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
    if "grounded" not in result or "score" not in result:
        return None
    return result
