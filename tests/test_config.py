from pathlib import Path

from ecobio_daily.config import load_digest_config, load_sources, load_topics


def test_load_sources_from_yaml(tmp_path: Path):
    path = tmp_path / "sources.yaml"
    path.write_text(
        """
sources:
  - id: example
    name: Example Feed
    type: rss
    url: https://example.org/feed.xml
""".strip(),
        encoding="utf-8",
    )

    sources = load_sources(path)

    assert sources[0].id == "example"
    assert sources[0].type == "rss"


def test_load_topics_from_yaml(tmp_path: Path):
    path = tmp_path / "topics.yaml"
    path.write_text(
        """
topics:
  - id: soil
    name: 土壤生态
    keywords:
      - soil
      - rhizosphere
""".strip(),
        encoding="utf-8",
    )

    topics = load_topics(path)

    assert topics[0].name == "土壤生态"
    assert topics[0].keywords == ["soil", "rhizosphere"]


def test_load_digest_config_from_yaml(tmp_path: Path):
    path = tmp_path / "digest.yaml"
    path.write_text(
        """
digest:
  title: EcoBio Daily
  language: zh
  output_pattern: "{year}/{month}/ecobio_digest_1d_{date}_zh.md"
  max_items: 12
  highlights: 3
  min_relevance_score: 2
  lookback_days: 2
""".strip(),
        encoding="utf-8",
    )

    config = load_digest_config(path)

    assert config.title == "EcoBio Daily"
    assert config.highlights == 3


def test_load_query_based_source_from_yaml(tmp_path: Path):
    path = tmp_path / "sources.yaml"
    path.write_text(
        """
sources:
  - id: openalex_ecobio
    name: OpenAlex EcoBio
    type: openalex
    query: ecology OR microbiome
    max_results: 25
""".strip(),
        encoding="utf-8",
    )

    sources = load_sources(path)

    assert sources[0].id == "openalex_ecobio"
    assert sources[0].url is None
    assert sources[0].query == "ecology OR microbiome"
    assert sources[0].max_results == 25
