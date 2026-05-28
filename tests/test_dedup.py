from __future__ import annotations

from datetime import date, datetime, timezone
from pathlib import Path

from ecobio_daily.dedup import (
    deduplicate_by_doi,
    extract_doi,
    filter_seen,
    load_seen_dois,
    save_seen_dois,
    update_seen,
)
from ecobio_daily.models import SourceItem  # noqa: F401  (used in tests)


def _item(item_id: str, url: str, source: str = "test") -> SourceItem:
    return SourceItem(
        id=item_id,
        title="t",
        url=url,
        source=source,
        published_at=datetime(2026, 5, 27, tzinfo=timezone.utc),
        summary="",
    )


# ---------- extract_doi ----------


def test_extract_doi_from_doi_org_url():
    item = _item("x", "https://doi.org/10.1016/j.jenvman.2026.130022")
    assert extract_doi(item) == "10.1016/j.jenvman.2026.130022"


def test_extract_doi_from_crossref_url():
    item = _item("x", "https://doi.org/10.1111/1758-2229.70366")
    assert extract_doi(item) == "10.1111/1758-2229.70366"


def test_extract_doi_normalizes_to_lowercase():
    item = _item("x", "https://DOI.ORG/10.1016/J.JENVMAN.2026.130022")
    assert extract_doi(item) == "10.1016/j.jenvman.2026.130022"


def test_extract_doi_falls_back_to_id_when_url_has_no_doi():
    item = _item("10.3389/fmicb.2026.7777", "https://example.org/some/path")
    assert extract_doi(item) == "10.3389/fmicb.2026.7777"


def test_extract_doi_returns_none_when_absent():
    item = _item("rss-12345", "https://example.org/blog/post-12345")
    assert extract_doi(item) is None


def test_extract_doi_strips_trailing_punctuation():
    item = _item("x", "https://doi.org/10.1016/j.foo.2026.000123.")
    assert extract_doi(item) == "10.1016/j.foo.2026.000123"


def test_extract_doi_normalizes_dataset_version_suffix():
    item = _item("x", "https://doi.org/10.17632/3rydxx5m7x.1")
    assert extract_doi(item) == "10.17632/3rydxx5m7x"


# ---------- filter_seen ----------


def test_filter_seen_drops_items_seen_on_prior_day():
    items = [
        _item("a", "https://doi.org/10.1234/aaa"),
        _item("b", "https://doi.org/10.1234/bbb"),
    ]
    seen = {"10.1234/aaa": "2026-05-26"}

    kept = filter_seen(items, seen, today=date(2026, 5, 27))

    assert [it.id for it in kept] == ["b"]


def test_filter_seen_keeps_items_seen_today_for_idempotent_reruns():
    items = [_item("a", "https://doi.org/10.1234/aaa")]
    seen = {"10.1234/aaa": "2026-05-27"}

    kept = filter_seen(items, seen, today=date(2026, 5, 27))

    assert [it.id for it in kept] == ["a"]


def test_filter_seen_keeps_items_with_no_doi():
    items = [_item("no-doi", "https://example.org/blog/x")]
    seen = {"10.1234/aaa": "2026-05-26"}

    kept = filter_seen(items, seen, today=date(2026, 5, 27))

    assert [it.id for it in kept] == ["no-doi"]


# ---------- update_seen ----------


def test_update_seen_adds_new_dois_with_today():
    seen: dict = {}
    items = [_item("a", "https://doi.org/10.1234/aaa")]

    update_seen(seen, items, today=date(2026, 5, 27))

    assert seen == {"10.1234/aaa": "2026-05-27"}


def test_update_seen_does_not_overwrite_earlier_date():
    seen = {"10.1234/aaa": "2026-05-20"}
    items = [_item("a", "https://doi.org/10.1234/aaa")]

    update_seen(seen, items, today=date(2026, 5, 27))

    assert seen["10.1234/aaa"] == "2026-05-20"


def test_update_seen_skips_items_without_doi():
    seen: dict = {}
    items = [_item("no-doi", "https://example.org/x")]

    update_seen(seen, items, today=date(2026, 5, 27))

    assert seen == {}


# ---------- load / save ----------


def test_load_seen_dois_returns_empty_when_file_missing(tmp_path: Path):
    assert load_seen_dois(tmp_path / "missing.json") == {}


def test_save_then_load_roundtrip(tmp_path: Path):
    path = tmp_path / "state" / "seen_dois.json"
    save_seen_dois(path, {"10.1234/aaa": "2026-05-26", "10.1234/bbb": "2026-05-27"})

    loaded = load_seen_dois(path)

    assert loaded == {"10.1234/aaa": "2026-05-26", "10.1234/bbb": "2026-05-27"}


# ---------- deduplicate_by_doi ----------


def test_deduplicate_by_doi_keeps_first_occurrence():
    items = [
        _item("first-pubmed", "https://pubmed.ncbi.nlm.nih.gov/12345/"),
        _item("second-europepmc", "https://doi.org/10.1234/aaa"),
    ]
    # Manually set first item's id to a DOI so both reference the same paper
    items[0] = SourceItem(
        id="10.1234/aaa",
        title="t",
        url="https://pubmed.ncbi.nlm.nih.gov/12345/",
        source="pubmed",
        published_at=items[0].published_at,
        summary="",
    )

    kept = deduplicate_by_doi(items)

    assert [it.url for it in kept] == ["https://pubmed.ncbi.nlm.nih.gov/12345/"]


def test_deduplicate_by_doi_collapses_dataset_versions():
    items = [
        _item("dataset", "https://doi.org/10.17632/3rydxx5m7x"),
        _item("dataset-v1", "https://doi.org/10.17632/3rydxx5m7x.1"),
    ]

    kept = deduplicate_by_doi(items)

    assert [it.id for it in kept] == ["dataset"]


def test_deduplicate_by_doi_preserves_items_without_doi():
    items = [
        _item("blog-1", "https://example.org/blog/x"),
        _item("blog-2", "https://example.org/blog/y"),
    ]

    kept = deduplicate_by_doi(items)

    assert len(kept) == 2
