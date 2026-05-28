from __future__ import annotations

import argparse
import os
import sys
from datetime import date
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from ecobio_daily.config import (
    load_digest_config,
    load_llm_config,
    load_sources,
    load_topics,
)
from ecobio_daily.llm import LLMClient, load_dotenv
from ecobio_daily.pipeline import run_pipeline
from ecobio_daily.run_metrics import RunMetrics


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate EcoBio Daily Markdown digest.")
    parser.add_argument("--date", required=True, help="Digest date in YYYY-MM-DD format.")
    parser.add_argument("--output-root", default=".", help="Directory where the report is written.")
    parser.add_argument("--sources", default="config/sources.yaml")
    parser.add_argument("--topics", default="config/topics.yaml")
    parser.add_argument("--digest", default="config/digest.yaml")
    parser.add_argument("--template", default="templates/digest_zh.md.j2")
    parser.add_argument("--llm-config", default="config/llm.yaml")
    parser.add_argument("--dotenv", default=".env")
    parser.add_argument(
        "--require-llm",
        action="store_true",
        help="Fail if LLM is disabled or the configured API key is unavailable.",
    )
    return parser.parse_args()


def _maybe_build_llm_client(
    llm_config_path: Path,
    dotenv_path: Path,
    require_llm: bool = False,
) -> LLMClient | None:
    if not llm_config_path.exists():
        if require_llm:
            raise RuntimeError(f"LLM config not found: {llm_config_path}")
        return None
    llm_config = load_llm_config(llm_config_path)
    if not llm_config.enabled:
        if require_llm:
            raise RuntimeError(f"LLM is disabled in {llm_config_path}")
        return None
    env = {**os.environ, **load_dotenv(dotenv_path)}
    missing_keys = sorted(
        {
            profile.api_key_env
            for profile in llm_config.profiles.values()
            if not env.get(profile.api_key_env)
        }
    )
    if require_llm and missing_keys:
        raise RuntimeError(
            "Missing required LLM API key environment variable(s): "
            + ", ".join(missing_keys)
        )
    cache_dir: Path | None = None
    if llm_config.budget.cache_llm_outputs:
        cache_dir = Path(llm_config.budget.cache_dir)
    return LLMClient(config=llm_config, env=env, cache_dir=cache_dir)


def _llm_max_items(llm_config_path: Path) -> int:
    if not llm_config_path.exists():
        return 12
    llm_config = load_llm_config(llm_config_path)
    return llm_config.budget.max_items_per_run


def main() -> None:
    args = parse_args()
    digest_date = date.fromisoformat(args.date)
    llm_client = _maybe_build_llm_client(
        Path(args.llm_config),
        Path(args.dotenv),
        require_llm=args.require_llm,
    )
    if llm_client is not None:
        print("LLM relevance scoring enabled.")
    else:
        print("LLM relevance scoring disabled (no config or llm.enabled=false).")
    metrics = RunMetrics(digest_date=digest_date)
    output_root = Path(args.output_root)
    llm_config_path = Path(args.llm_config)
    output_path = run_pipeline(
        sources=load_sources(Path(args.sources)),
        topics=load_topics(Path(args.topics)),
        digest_config=load_digest_config(Path(args.digest)),
        digest_date=digest_date,
        template_path=Path(args.template),
        output_root=output_root,
        llm_client=llm_client,
        llm_max_items=_llm_max_items(llm_config_path),
        metrics=metrics,
    )
    metrics.save(output_root / "data" / "runs" / f"{digest_date.isoformat()}.json")
    print(f"Wrote digest: {output_path}")


if __name__ == "__main__":
    main()
