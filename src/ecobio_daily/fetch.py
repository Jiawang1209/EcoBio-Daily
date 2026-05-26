from __future__ import annotations

from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
import re

import feedparser
import httpx

from ecobio_daily.config import SourceConfig
from ecobio_daily.models import SourceItem


def _parse_datetime(value: str | None) -> datetime:
    if not value:
        return datetime.now(timezone.utc)
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        parsed = parsedate_to_datetime(value)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed


def _parse_publication_date(value: str | None) -> datetime:
    if not value:
        return datetime.now(timezone.utc)
    cleaned = value.strip().rstrip(".")
    for fmt in ("%Y-%m-%d", "%Y %b %d", "%Y %b", "%Y"):
        try:
            parsed = datetime.strptime(cleaned, fmt)
            return parsed.replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    return _parse_datetime(cleaned)


def _doi_url(doi: str | None) -> str:
    if not doi:
        return ""
    normalized = doi.removeprefix("https://doi.org/").removeprefix("http://doi.org/")
    return f"https://doi.org/{normalized}"


def _openalex_abstract(inverted_index: dict[str, list[int]] | None) -> str:
    if not inverted_index:
        return ""
    words_by_position: dict[int, str] = {}
    for word, positions in inverted_index.items():
        for position in positions:
            words_by_position[position] = word
    return " ".join(words_by_position[position] for position in sorted(words_by_position))


def _source_with_journal(source_name: str, journal: str | None) -> str:
    if not journal:
        return source_name
    return f"{source_name}: {journal}"


def _entry_datetime(entry: dict) -> datetime:
    value = (
        entry.get("published")
        or entry.get("updated")
        or entry.get("prism_publicationdate")
    )
    return _parse_datetime(value)


def parse_rss(xml: str, source_id: str, source_name: str) -> list[SourceItem]:
    feed = feedparser.parse(xml)
    items: list[SourceItem] = []
    for entry in feed.entries:
        url = entry.get("link", "")
        item_id = entry.get("id") or entry.get("guid") or url
        item = SourceItem(
            id=str(item_id),
            title=entry.get("title", "").strip(),
            url=url,
            source=source_name,
            published_at=_entry_datetime(entry),
            summary=entry.get("summary", ""),
            tags=[source_id],
        )
        if item.title and item.url:
            items.append(item)
    return items


def parse_openalex(payload: dict, source_id: str, source_name: str) -> list[SourceItem]:
    items: list[SourceItem] = []
    for work in payload.get("results", []):
        location = work.get("primary_location") or {}
        source = location.get("source") or {}
        doi = work.get("doi")
        url = location.get("landing_page_url") or _doi_url(doi) or work.get("id", "")
        authors = [
            authorship.get("author", {}).get("display_name", "")
            for authorship in work.get("authorships", [])
        ]
        item = SourceItem(
            id=doi or work.get("id", url),
            title=(work.get("display_name") or "").strip(),
            url=url,
            source=_source_with_journal(source_name, source.get("display_name")),
            published_at=_parse_publication_date(work.get("publication_date")),
            summary=_openalex_abstract(work.get("abstract_inverted_index")),
            authors=[author for author in authors if author],
            tags=[source_id],
        )
        if item.title and item.url:
            items.append(item)
    return items


def parse_europe_pmc(payload: dict, source_id: str, source_name: str) -> list[SourceItem]:
    results = payload.get("resultList", {}).get("result", [])
    items: list[SourceItem] = []
    for result in results:
        doi = result.get("doi")
        pmid = result.get("pmid") or result.get("id")
        url = _doi_url(doi)
        if not url and pmid:
            url = f"https://europepmc.org/article/MED/{pmid}"
        authors = [
            author.strip()
            for author in (result.get("authorString") or "").split(",")
            if author.strip()
        ]
        item = SourceItem(
            id=doi or pmid or result.get("title", ""),
            title=(result.get("title") or "").strip(),
            url=url,
            source=_source_with_journal(source_name, result.get("journalTitle")),
            published_at=_parse_publication_date(
                result.get("firstPublicationDate") or result.get("pubYear")
            ),
            summary=result.get("abstractText") or "",
            authors=authors,
            tags=[source_id],
        )
        if item.title and item.url:
            items.append(item)
    return items


def parse_pubmed(payload: dict, source_id: str, source_name: str) -> list[SourceItem]:
    result = payload.get("result", {})
    items: list[SourceItem] = []
    for uid in result.get("uids", []):
        record = result.get(uid, {})
        authors = [author.get("name", "") for author in record.get("authors", [])]
        item = SourceItem(
            id=record.get("uid") or uid,
            title=(record.get("title") or "").strip().rstrip("."),
            url=f"https://pubmed.ncbi.nlm.nih.gov/{uid}/",
            source=_source_with_journal(source_name, record.get("fulljournalname")),
            published_at=_parse_publication_date(record.get("pubdate")),
            summary=record.get("sorttitle") or "",
            authors=[author for author in authors if author],
            tags=[source_id],
        )
        if item.title and item.url:
            items.append(item)
    return items


def _fetch_rss(source: SourceConfig, timeout_seconds: float) -> list[SourceItem]:
    if source.url is None:
        raise ValueError(f"RSS source requires url: {source.id}")
    response = httpx.get(str(source.url), timeout=timeout_seconds, follow_redirects=True)
    response.raise_for_status()
    return parse_rss(response.text, source_id=source.id, source_name=source.name)


def _fetch_openalex(source: SourceConfig, timeout_seconds: float) -> list[SourceItem]:
    if not source.query:
        raise ValueError(f"OpenAlex source requires query: {source.id}")
    response = httpx.get(
        "https://api.openalex.org/works",
        params={
            "search": source.query,
            "per-page": source.max_results,
            "sort": "publication_date:desc",
        },
        timeout=timeout_seconds,
        follow_redirects=True,
    )
    response.raise_for_status()
    return parse_openalex(response.json(), source_id=source.id, source_name=source.name)


def _fetch_europe_pmc(source: SourceConfig, timeout_seconds: float) -> list[SourceItem]:
    if not source.query:
        raise ValueError(f"Europe PMC source requires query: {source.id}")
    response = httpx.get(
        "https://www.ebi.ac.uk/europepmc/webservices/rest/search",
        params={
            "query": source.query,
            "format": "json",
            "pageSize": source.max_results,
            "sort": "FIRST_PDATE_D desc",
        },
        timeout=timeout_seconds,
        follow_redirects=True,
    )
    response.raise_for_status()
    return parse_europe_pmc(response.json(), source_id=source.id, source_name=source.name)


def _fetch_pubmed(source: SourceConfig, timeout_seconds: float) -> list[SourceItem]:
    if not source.query:
        raise ValueError(f"PubMed source requires query: {source.id}")
    search_response = httpx.get(
        "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi",
        params={
            "db": "pubmed",
            "term": source.query,
            "retmode": "json",
            "retmax": source.max_results,
            "sort": "pub+date",
        },
        timeout=timeout_seconds,
        follow_redirects=True,
    )
    search_response.raise_for_status()
    ids = search_response.json().get("esearchresult", {}).get("idlist", [])
    if not ids:
        return []
    summary_response = httpx.get(
        "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi",
        params={
            "db": "pubmed",
            "id": ",".join(ids),
            "retmode": "json",
        },
        timeout=timeout_seconds,
        follow_redirects=True,
    )
    summary_response.raise_for_status()
    return parse_pubmed(summary_response.json(), source_id=source.id, source_name=source.name)


def _fetch_biorxiv_api(source: SourceConfig, timeout_seconds: float) -> list[SourceItem]:
    if not source.query:
        raise ValueError(f"bioRxiv API source requires query: {source.id}")
    # bioRxiv's public details endpoint is date-range based. Query filtering stays
    # local so this backend can share the same config shape as other sources.
    today = datetime.now(timezone.utc).date()
    start = today - timedelta(days=7)
    url = f"https://api.biorxiv.org/details/biorxiv/{start.isoformat()}/{today.isoformat()}"
    response = httpx.get(url, timeout=timeout_seconds, follow_redirects=True)
    response.raise_for_status()
    query_terms = [term.lower() for term in re.findall(r"[A-Za-z][A-Za-z -]+", source.query)]
    items: list[SourceItem] = []
    for record in response.json().get("collection", []):
        text = f"{record.get('title', '')}\n{record.get('abstract', '')}".lower()
        if query_terms and not any(term.strip() and term.strip() in text for term in query_terms):
            continue
        doi = record.get("doi", "")
        item = SourceItem(
            id=doi or record.get("title", ""),
            title=(record.get("title") or "").strip(),
            url=f"https://www.biorxiv.org/content/{doi}v{record.get('version', '1')}" if doi else "",
            source=source.name,
            published_at=_parse_publication_date(record.get("date")),
            summary=record.get("abstract") or "",
            authors=[author.strip() for author in (record.get("authors") or "").split(";") if author.strip()],
            tags=[source.id],
        )
        if item.title and item.url:
            items.append(item)
        if len(items) >= source.max_results:
            break
    return items


def fetch_source(source: SourceConfig, timeout_seconds: float = 20.0) -> list[SourceItem]:
    fetchers = {
        "rss": _fetch_rss,
        "openalex": _fetch_openalex,
        "europe_pmc": _fetch_europe_pmc,
        "pubmed": _fetch_pubmed,
        "biorxiv_api": _fetch_biorxiv_api,
    }
    fetcher = fetchers.get(source.type)
    if fetcher is None:
        raise ValueError(f"Unsupported source type: {source.type}")
    return fetcher(source, timeout_seconds)
