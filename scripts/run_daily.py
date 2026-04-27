from __future__ import annotations

import argparse
import sys
from datetime import date
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from ecobio_daily.config import load_digest_config, load_sources, load_topics
from ecobio_daily.pipeline import run_pipeline


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate EcoBio Daily Markdown digest.")
    parser.add_argument("--date", required=True, help="Digest date in YYYY-MM-DD format.")
    parser.add_argument("--output-root", default=".", help="Directory where the report is written.")
    parser.add_argument("--sources", default="config/sources.yaml")
    parser.add_argument("--topics", default="config/topics.yaml")
    parser.add_argument("--digest", default="config/digest.yaml")
    parser.add_argument("--template", default="templates/digest_zh.md.j2")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    digest_date = date.fromisoformat(args.date)
    output_path = run_pipeline(
        sources=load_sources(Path(args.sources)),
        topics=load_topics(Path(args.topics)),
        digest_config=load_digest_config(Path(args.digest)),
        digest_date=digest_date,
        template_path=Path(args.template),
        output_root=Path(args.output_root),
    )
    print(f"Wrote digest: {output_path}")


if __name__ == "__main__":
    main()
