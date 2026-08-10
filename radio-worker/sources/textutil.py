"""Shared text helpers for source adapters."""
from __future__ import annotations

import html
import re
from html.parser import HTMLParser
from typing import List


class _TextExtractor(HTMLParser):
    """Collapse HTML into readable, single-spaced plain text."""

    def __init__(self):
        super().__init__()
        self._parts: List[str] = []

    def handle_starttag(self, tag, attrs):
        if tag in ("br", "p", "li", "div"):
            self._parts.append("\n")

    def handle_data(self, data):
        self._parts.append(data)

    def get_text(self) -> str:
        text = "".join(self._parts)
        text = html.unescape(text)
        text = re.sub(r"\s+", " ", text).strip()
        return text


def html_to_text(content_html: str) -> str:
    """Convert an HTML fragment (Mastodon post, RSS description) to plain text."""
    if not content_html:
        return ""
    parser = _TextExtractor()
    parser.feed(content_html)
    return parser.get_text()
