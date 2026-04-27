from pathlib import Path

from ecobio_daily.fetch import parse_rss


def test_parse_rss_fixture():
    xml = Path("tests/fixtures/sample_feed.xml").read_text(encoding="utf-8")

    items = parse_rss(xml, source_id="sample", source_name="Sample Feed")

    assert len(items) == 2
    assert items[0].id == "paper-1"
    assert items[0].source == "Sample Feed"
    assert items[0].title == "Soil microbial diversity increases drought resilience"
    assert items[0].summary.startswith("Microbial diversity")
