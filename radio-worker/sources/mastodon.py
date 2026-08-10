"""Mastodon source adapter.

Polls a public Mastodon account's posts — a natural free text source for scanner
feeds. No authentication is required for public timelines:

    GET {instance}/api/v1/accounts/lookup?acct=user@host      -> resolve id
    GET {instance}/api/v1/accounts/{id}/statuses?since_id=... -> new posts

Each post's HTML content is stripped to plain text and treated as one
transmission. Dedup is by Mastodon status id (also used as the since_id cursor).
"""
from __future__ import annotations

from typing import List, Optional

import httpx

import config
from sources.base import Call, RadioSource
from sources.textutil import html_to_text


def status_to_text(content_html: str) -> str:
    """Public helper (unit-tested): Mastodon HTML content -> plain text."""
    return html_to_text(content_html)


def statuses_to_calls(statuses: list, instance: str) -> List[Call]:
    """Map a Mastodon statuses payload to Call objects (pure, testable)."""
    calls: List[Call] = []
    for s in statuses:
        text = status_to_text(s.get("content", ""))
        calls.append(
            Call(
                external_id=f"mastodon-{s.get('id')}",
                source="mastodon",
                transcript=text,
                timestamp=s.get("created_at"),
                extra={"url": s.get("url"), "instance": instance},
            )
        )
    return calls


def max_status_id(statuses: list) -> Optional[str]:
    """Return the largest (newest) numeric status id in a payload, or None."""
    ids = []
    for s in statuses:
        try:
            ids.append(int(s.get("id")))
        except (TypeError, ValueError):
            continue
    return str(max(ids)) if ids else None


class MastodonSource(RadioSource):
    name = "mastodon"

    def __init__(self, since_id: Optional[str] = None):
        if not config.MASTODON_INSTANCE or not config.MASTODON_ACCOUNT:
            raise ValueError(
                "MASTODON_INSTANCE and MASTODON_ACCOUNT must be set "
                "(e.g. https://mastodon.social and someScanner@mastodon.social)."
            )
        self.instance = config.MASTODON_INSTANCE.rstrip("/")
        self.account = config.MASTODON_ACCOUNT.lstrip("@")
        self.since_id = since_id
        self._account_id: Optional[str] = None

    def _resolve_account_id(self) -> Optional[str]:
        if self._account_id:
            return self._account_id
        # A bare numeric account is used directly.
        if self.account.isdigit():
            self._account_id = self.account
            return self._account_id
        try:
            resp = httpx.get(
                f"{self.instance}/api/v1/accounts/lookup",
                params={"acct": self.account},
                timeout=15.0,
            )
            resp.raise_for_status()
            self._account_id = str(resp.json().get("id"))
        except (httpx.HTTPError, ValueError) as exc:
            print(f"[mastodon] account lookup failed for {self.account!r}: {exc}", flush=True)
            return None
        return self._account_id

    def fetch_new_calls(self) -> List[Call]:
        account_id = self._resolve_account_id()
        if not account_id:
            return []

        params = {
            "limit": 40,
            "exclude_reblogs": "true",
            "exclude_replies": "true" if config.MASTODON_EXCLUDE_REPLIES else "false",
        }
        if self.since_id:
            params["since_id"] = self.since_id

        try:
            resp = httpx.get(
                f"{self.instance}/api/v1/accounts/{account_id}/statuses",
                params=params,
                timeout=20.0,
            )
            resp.raise_for_status()
            statuses = resp.json()
        except (httpx.HTTPError, ValueError) as exc:
            print(f"[mastodon] fetch failed: {exc}", flush=True)
            return []

        if not isinstance(statuses, list) or not statuses:
            # First run with no cursor: set the cursor to newest so we only
            # ingest posts created from here on out.
            return []

        newest = max_status_id(statuses)
        first_run = self.since_id is None
        if newest:
            self.since_id = newest

        # On the very first poll (no cursor) we just prime the cursor and skip
        # the backlog, matching the OpenMHz "only fresh traffic" behaviour.
        if first_run:
            print(f"[mastodon] primed cursor at {self.since_id}, skipping backlog", flush=True)
            return []

        return statuses_to_calls(statuses, self.instance)
