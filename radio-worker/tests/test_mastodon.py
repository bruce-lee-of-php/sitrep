"""Unit tests for the Mastodon source's pure helpers (no network).

The HTTP polling itself is thin; the logic worth testing is HTML->text
conversion, status mapping, and cursor (since_id) math.
"""
from sources.mastodon import max_status_id, status_to_text, statuses_to_calls


def test_status_to_text_strips_html_and_unescapes():
    html = (
        "<p>Units respond, <a href='x'>protest</a> at 5th &amp; Main"
        "<br>~200 people</p><p>code 3</p>"
    )
    text = status_to_text(html)
    assert "<" not in text and ">" not in text
    assert "5th & Main" in text
    assert "protest" in text
    assert "200 people" in text
    # paragraphs/brs collapse to single-spaced text
    assert "  " not in text


def test_status_to_text_empty():
    assert status_to_text("") == ""


def test_statuses_to_calls_maps_fields():
    statuses = [
        {"id": "111", "content": "<p>Checkpoint on Broadway</p>",
         "created_at": "2026-08-10T00:00:00.000Z", "url": "http://x/1"},
        {"id": "112", "content": "<p>Arrest at 1st and Oak</p>",
         "created_at": "2026-08-10T00:01:00.000Z", "url": "http://x/2"},
    ]
    calls = statuses_to_calls(statuses, "https://mastodon.social")
    assert [c.external_id for c in calls] == ["mastodon-111", "mastodon-112"]
    assert all(c.source == "mastodon" for c in calls)
    assert calls[0].transcript == "Checkpoint on Broadway"
    assert calls[1].extra["url"] == "http://x/2"


def test_max_status_id_returns_newest_numeric():
    statuses = [{"id": "9"}, {"id": "123"}, {"id": "45"}]
    assert max_status_id(statuses) == "123"


def test_max_status_id_handles_empty_and_bad():
    assert max_status_id([]) is None
    assert max_status_id([{"id": None}, {"nope": 1}]) is None
