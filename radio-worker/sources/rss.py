"""RSS / Atom source adapter.

Polls one or more feed URLs and turns each item into a transmission. Works with
any RSS 2.0 or Atom feed — including a Mastodon account's RSS endpoint
(``https://<instance>/@<user>.rss``), which needs no auth.

Parsing uses the standard library (xml.etree) so the text-only build stays
dependency-light; the parse/mapping helpers are pure and unit-tested.
"""
from __future__ import annotations

import hashlib
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from typing import Dict, List, Optional, Set

import httpx

import config
from sources.base import Call, RadioSource
from sources.textutil import html_to_text


@dataclass
class FeedItem:
    guid: str
    title: str
    summary: str
    link: Optional[str] = None

    def text(self) -> str:
        """Combined transcript text: title then body, de-duplicated."""
        title = (self.title or "").strip()
        summary = (self.summary or "").strip()
        if summary and title and summary.startswith(title):
            return summary
        return " — ".join(p for p in (title, summary) if p).strip(" —")


def _local(tag: str) -> str:
    """Strip an XML namespace: '{ns}entry' -> 'entry'."""
    return tag.rsplit("}", 1)[-1]


def _find_child_text(elem, names) -> str:
    for child in elem:
        if _local(child.tag) in names:
            # Atom links carry the URL in an attribute, handled separately.
            if child.text:
                return child.text.strip()
    return ""


def _atom_link(entry) -> Optional[str]:
    for child in entry:
        if _local(child.tag) == "link":
            href = child.attrib.get("href")
            if href and child.attrib.get("rel", "alternate") == "alternate":
                return href
    return None


def parse_feed(xml_bytes: bytes) -> List[FeedItem]:
    """Parse RSS 2.0 or Atom bytes into FeedItems (pure, no network)."""
    try:
        root = ET.fromstring(xml_bytes)
    except ET.ParseError:
        return []

    items: List[FeedItem] = []

    # RSS 2.0: <rss><channel><item>...  |  RDF/RSS1.0: <item> at any depth.
    rss_items = [e for e in root.iter() if _local(e.tag) == "item"]
    if rss_items:
        for it in rss_items:
            title = _find_child_text(it, {"title"})
            summary = _find_child_text(it, {"description", "encoded", "summary"})
            link = _find_child_text(it, {"link"})
            guid = _find_child_text(it, {"guid", "id"}) or link or _hash(title + summary)
            items.append(FeedItem(guid=guid, title=title, summary=html_to_text(summary), link=link or None))
        return items

    # Atom: <feed><entry>...
    entries = [e for e in root.iter() if _local(e.tag) == "entry"]
    for en in entries:
        title = _find_child_text(en, {"title"})
        summary = _find_child_text(en, {"summary", "content"})
        guid = _find_child_text(en, {"id"})
        link = _atom_link(en)
        guid = guid or link or _hash(title + summary)
        items.append(FeedItem(guid=guid, title=title, summary=html_to_text(summary), link=link))
    return items


def _hash(text: str) -> str:
    return hashlib.sha1(text.encode("utf-8")).hexdigest()[:16]


def item_to_call(item: FeedItem, feed_url: str) -> Call:
    return Call(
        external_id="rss-" + _hash(feed_url + "|" + item.guid),
        source="rss",
        transcript=item.text(),
        extra={"feed": feed_url, "link": item.link, "guid": item.guid},
    )


class RssSource(RadioSource):
    name = "rss"

    def __init__(self, feeds: Optional[List[str]] = None):
        raw = feeds if feeds is not None else config.RSS_FEEDS
        self.feeds = [f.strip() for f in raw if f and f.strip()]
        if not self.feeds:
            raise ValueError(
                "RSS_FEEDS is empty — set a comma-separated list of feed URLs "
                "(e.g. https://mastodon.social/@someScanner.rss)."
            )
        # Per-feed set of guids already seen this process; store dedup covers
        # restarts. Primed on first poll so we skip each feed's backlog.
        self._seen: Dict[str, Set[str]] = {f: set() for f in self.feeds}
        self._primed: Set[str] = set()

    def _fetch_feed(self, url: str) -> List[FeedItem]:
        try:
            resp = httpx.get(url, timeout=20.0, follow_redirects=True)
            resp.raise_for_status()
            return parse_feed(resp.content)
        except httpx.HTTPError as exc:
            print(f"[rss] fetch failed for {url}: {exc}", flush=True)
            return []

    def fetch_new_calls(self) -> List[Call]:
        calls: List[Call] = []
        for url in self.feeds:
            items = self._fetch_feed(url)
            seen = self._seen[url]

            if url not in self._primed:
                # First poll: remember what's there and skip the backlog.
                for it in items:
                    seen.add(it.guid)
                self._primed.add(url)
                print(f"[rss] primed {url} with {len(items)} existing item(s)", flush=True)
                continue

            for it in items:
                if it.guid in seen:
                    continue
                seen.add(it.guid)
                calls.append(item_to_call(it, url))
        return calls
