from pathlib import Path
from datetime import date

from ecobio_daily.fetch import parse_rss


def test_parse_rss_fixture():
    xml = Path("tests/fixtures/sample_feed.xml").read_text(encoding="utf-8")

    items = parse_rss(xml, source_id="sample", source_name="Sample Feed")

    assert len(items) == 2
    assert items[0].id == "paper-1"
    assert items[0].source == "Sample Feed"
    assert items[0].title == "Soil microbial diversity increases drought resilience"
    assert items[0].summary.startswith("Microbial diversity")


def test_parse_rss_uses_biorxiv_publication_date_fields():
    xml = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0"
  xmlns:prism="http://prismstandard.org/namespaces/basic/2.0/">
  <channel>
    <title>bioRxiv Ecology</title>
    <item>
      <title>Helminth infection dynamics in rehabilitating slow lorises</title>
      <link>https://example.org/paper-1</link>
      <guid>paper-1</guid>
      <updated>2026-04-27</updated>
      <prism:publicationDate>2026-04-27</prism:publicationDate>
      <description>Parasite dynamics changed over time.</description>
    </item>
  </channel>
</rss>
"""

    items = parse_rss(xml, source_id="biorxiv_ecology", source_name="bioRxiv Ecology")

    assert items[0].published_date == date(2026, 4, 27)
