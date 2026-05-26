from __future__ import annotations

import os
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import httpx

from ecobio_daily.config import LLMConfig, LLMProfile
from ecobio_daily.llm_cache import cache_key, read_cache, write_cache


class LLMError(RuntimeError):
    pass


class LLMMissingKeyError(LLMError):
    pass


class LLMRequestError(LLMError):
    pass


def load_dotenv(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    result: dict[str, str] = {}
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        result[key.strip()] = value.strip()
    return result


class LLMClient:
    def __init__(
        self,
        config: LLMConfig,
        http_client: httpx.Client | None = None,
        env: Mapping[str, str] | None = None,
        cache_dir: Path | None = None,
    ):
        self.config = config
        self._http_client = http_client
        self._env: Mapping[str, str] = env if env is not None else os.environ
        self._cache_dir = cache_dir

    def resolve_profile(
        self,
        name: str | None = None,
        task: str | None = None,
    ) -> LLMProfile:
        if name is not None:
            return self.config.profiles[name]
        if task is not None and task in self.config.routing:
            return self.config.profiles[self.config.routing[task]]
        return self.config.profiles[self.config.active_profile]

    def chat(
        self,
        messages: list[dict[str, Any]],
        profile: LLMProfile | None = None,
        task: str | None = None,
        response_format: str | None = None,
    ) -> str:
        if profile is None:
            profile = self.resolve_profile(task=task)

        api_key = self._env.get(profile.api_key_env, "")
        if not api_key:
            raise LLMMissingKeyError(
                f"missing API key: env var {profile.api_key_env} is not set"
            )

        key: str | None = None
        if self._cache_dir is not None:
            key = cache_key(
                model=profile.model,
                messages=messages,
                response_format=response_format,
                temperature=profile.temperature,
            )
            cached = read_cache(self._cache_dir, key)
            if cached is not None:
                return cached

        payload: dict[str, Any] = {
            "model": profile.model,
            "messages": messages,
            "temperature": profile.temperature,
            "max_tokens": profile.max_tokens,
        }
        if response_format is not None:
            payload["response_format"] = {"type": response_format}

        url = f"{str(profile.base_url).rstrip('/')}/chat/completions"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

        client = self._http_client or httpx.Client(timeout=profile.timeout_seconds)
        try:
            response = client.post(url, json=payload, headers=headers)
        except httpx.HTTPError as exc:
            raise LLMRequestError(f"HTTP request failed: {exc}") from exc

        if response.status_code >= 400:
            raise LLMRequestError(
                f"LLM gateway returned {response.status_code}: {response.text[:500]}"
            )

        data = response.json()
        content = data["choices"][0]["message"]["content"]

        if self._cache_dir is not None and key is not None:
            write_cache(self._cache_dir, key, content, profile.model)

        return content
