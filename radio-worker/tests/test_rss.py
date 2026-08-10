"""Unit tests for the RSS/Atom source (pure parsing + dedup logic, no network)."""
from sources.rss import FeedItem, RssSource, item_to_call, parse_feed

RSS_2 = b"""<?xml version="1.0"?>
<rss version="2.0">
  <channel>
    <title>Scanner Feed</title>
    <item>
      <title>Protest downtown</title>
      <description>&lt;p&gt;Crowd forming at 5th &amp;amp; Main, ~200 people&lt;/p&gt;</description>
      <link>https://example.org/1</link>
      <guid>https://example.org/1</guid>
    </item>
    <item>
      <title>Checkpoint</title>
      <description>Units set up on Broadway</description>
      <guid>abc-123</guid>
    </item>
  </channel>
</rss>"""

ATOM = b"""<?xml version="1.0"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <title>Scanner</title>
  <entry>
    <title>Arrest made</title>
    <summary>Subject in custody at 1st and Oak</summary>
    <id>tag:example.org,2026:1</id>
    <link rel="alternate" href="https://example.org/a1"/>
  </entry>
</feed>"""


def test_parse_rss2_items_and_html_strip():
    items = parse_feed(RSS_2)
    assert len(items) == 2
    first = items[0]
    assert first.title == "Protest downtown"
    # HTML entities/tags in the description are decoded and stripped.
    assert "<" not in first.summary
    assert "5th & Main" in first.summary
    assert first.guid == "https://example.org/1"


def test_parse_atom_entries_and_link():
    items = parse_feed(ATOM)
    assert len(items) == 1
    it = items[0]
    assert it.title == "Arrest made"
    assert "1st and Oak" in it.summary
    assert it.guid == "tag:example.org,2026:1"
    assert it.link == "https://example.org/a1"


def test_parse_bad_xml_returns_empty():
    assert parse_feed(b"<not xml") == []


def test_feeditem_text_combines_title_and_summary():
    it = FeedItem(guid="g", title="Protest", summary="at 5th and Main")
    assert it.text() == "Protest — at 5th and Main"


def test_item_to_call_stable_id_per_feed():
    it = FeedItem(guid="g1", title="t", summary="s")
    c1 = item_to_call(it, "https://feed.a")
    c2 = item_to_call(it, "https://feed.a")
    c3 = item_to_call(it, "https://feed.b")
    assert c1.external_id == c2.external_id      # deterministic
    assert c1.external_id != c3.external_id      # namespaced by feed
    assert c1.source == "rss"


def test_source_primes_then_delivers(monkeypatch):
    """First poll skips backlog; a newly-appeared item is delivered next poll."""
    calls_by_poll = [
        parse_feed(RSS_2),                                   # first poll: 2 items (backlog)
        parse_feed(RSS_2) + [FeedItem("new-9", "New incident", "protest at Elm")],
    ]
    src = RssSource(feeds=["https://feed.test"])
    it = iter(calls_by_poll)
    monkeypatch.setattr(src, "_fetch_feed", lambda url: next(it))

    first = src.fetch_new_calls()
    assert first == []                                       # backlog skipped

    second = src.fetch_new_calls()
    assert len(second) == 1
    assert "New incident" in second[0].transcript
