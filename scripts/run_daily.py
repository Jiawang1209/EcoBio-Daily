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
    return parser.parse_args()


def _maybe_build_llm_client(llm_config_path: Path, dotenv_path: Path) -> LLMClient | None:
    if not llm_config_path.exists():
        return None
    llm_config = load_llm_config(llm_config_path)
    if not llm_config.enabled:
        return None
    env = {**os.environ, **load_dotenv(dotenv_path)}
    cache_dir: Path | None = None
    if llm_config.budget.cache_llm_outputs:
        cache_dir = Path(llm_config.budget.cache_dir)
    return LLMClient(config=llm_config, env=env, cache_dir=cache_dir)


def main() -> None:
    args = parse_args()
    digest_date = date.fromisoformat(args.date)
    llm_client = _maybe_build_llm_client(Path(args.llm_config), Path(args.dotenv))
    if llm_client is not None:
        print("LLM relevance scoring enabled.")
    else:
        print("LLM relevance scoring disabled (no config or llm.enabled=false).")
    output_path = run_pipeline(
        sources=load_sources(Path(args.sources)),
        topics=load_topics(Path(args.topics)),
        digest_config=load_digest_config(Path(args.digest)),
        digest_date=digest_date,
        template_path=Path(args.template),
        output_root=Path(args.output_root),
        llm_client=llm_client,
    )
    print(f"Wrote digest: {output_path}")


if __name__ == "__main__":
    main()
