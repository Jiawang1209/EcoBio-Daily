from pathlib import Path
from datetime import date

from ecobio_daily.fetch import parse_europe_pmc, parse_openalex, parse_pubmed, parse_rss


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


def test_parse_openalex_maps_work_to_source_item():
    payload = {
        "results": [
            {
                "id": "https://openalex.org/W123",
                "doi": "https://doi.org/10.1234/example",
                "display_name": "Microbial ecology changes under drought",
                "publication_date": "2026-05-20",
                "abstract_inverted_index": {
                    "Microbial": [0],
                    "communities": [1],
                    "changed": [2],
                    "under": [3],
                    "drought.": [4],
                },
                "authorships": [
                    {"author": {"display_name": "Ada Lovelace"}},
                    {"author": {"display_name": "Grace Hopper"}},
                ],
                "primary_location": {
                    "source": {"display_name": "Ecology Letters"},
                    "landing_page_url": "https://example.org/paper",
                },
            }
        ]
    }

    items = parse_openalex(payload, source_id="openalex", source_name="OpenAlex")

    assert len(items) == 1
    assert items[0].id == "https://doi.org/10.1234/example"
    assert items[0].title == "Microbial ecology changes under drought"
    assert items[0].summary == "Microbial communities changed under drought."
    assert items[0].authors == ["Ada Lovelace", "Grace Hopper"]
    assert items[0].published_date == date(2026, 5, 20)
    assert items[0].tags == ["openalex"]


def test_parse_europe_pmc_maps_result_to_source_item():
    payload = {
        "resultList": {
            "result": [
                {
                    "id": "123456",
                    "doi": "10.5678/example",
                    "title": "Metagenomics reveals soil carbon cycling",
                    "abstractText": "A soil microbiome study.",
                    "firstPublicationDate": "2026-05-19",
                    "authorString": "Lovelace A, Hopper G.",
                    "journalTitle": "Environmental Microbiology",
                }
            ]
        }
    }

    items = parse_europe_pmc(payload, source_id="europe_pmc", source_name="Europe PMC")

    assert items[0].id == "10.5678/example"
    assert items[0].url == "https://doi.org/10.5678/example"
    assert items[0].source == "Europe PMC: Environmental Microbiology"
    assert items[0].summary == "A soil microbiome study."
    assert items[0].published_date == date(2026, 5, 19)


def test_parse_pubmed_maps_esummary_records_to_source_item():
    payload = {
        "result": {
            "uids": ["987654"],
            "987654": {
                "uid": "987654",
                "title": "Microbiome dynamics in restored wetlands.",
                "pubdate": "2026 May 18",
                "fulljournalname": "Applied and Environmental Microbiology",
                "authors": [{"name": "Lovelace A"}, {"name": "Hopper G"}],
                "elocationid": "doi: 10.9012/example",
            },
        }
    }

    items = parse_pubmed(payload, source_id="pubmed", source_name="PubMed")

    assert items[0].id == "987654"
    assert items[0].url == "https://pubmed.ncbi.nlm.nih.gov/987654/"
    assert items[0].source == "PubMed: Applied and Environmental Microbiology"
    assert items[0].authors == ["Lovelace A", "Hopper G"]
    assert items[0].published_date == date(2026, 5, 18)
