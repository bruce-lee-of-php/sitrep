"""OpenMHz source adapter.

Polls the free OpenMHz public API for new calls on a configured system.

    GET {base}/{system}/calls/newer?time={cursor}&filter-type={type}&filter-code={code}

The response is a JSON object with a ``calls`` array; each call carries an
``_id``, a ``url`` (CDN link to the m4a audio), ``talkgroupNum``, ``time`` and
``len``. The ``time`` cursor is a millisecond value (unix seconds with the
first three decimals appended, no dot).

Reference: https://github.com/spdconvos/encryptedbot_py/blob/main/API/OPENMHZ_API.md
"""
from __future__ import annotations

import time as _time
from datetime import datetime, timezone
from typing import List, Optional

import httpx

import config
from sources.base import Call, RadioSource


def _iso_to_cursor_ms(iso_ts: str) -> Optional[int]:
    """Convert an ISO8601 call time to OpenMHz's millisecond cursor value."""
    if not iso_ts:
        return None
    try:
        # OpenMHz uses e.g. "2021-01-01T20:30:15.000Z"
        cleaned = iso_ts.replace("Z", "+00:00")
        dt = datetime.fromisoformat(cleaned)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return int(dt.timestamp() * 1000)
    except ValueError:
        return None


class OpenMHzSource(RadioSource):
    name = "openmhz"

    def __init__(self, cursor_ms: Optional[int] = None):
        if not config.OPENMHZ_SYSTEM:
            raise ValueError(
                "OPENMHZ_SYSTEM is not set — set it to a system short name "
                "from https://openmhz.com (e.g. 'kcers1b')."
            )
        self.system = config.OPENMHZ_SYSTEM
        self.base_url = config.OPENMHZ_BASE_URL
        # Cursor is a millisecond timestamp; start "now" if none provided so we
        # only ingest fresh traffic on first run.
        self.cursor_ms = cursor_ms if cursor_ms is not None else int(_time.time() * 1000)

    def _params(self) -> dict:
        params = {"time": self.cursor_ms}
        if config.OPENMHZ_FILTER_CODE:
            params["filter-type"] = config.OPENMHZ_FILTER_TYPE
            params["filter-code"] = config.OPENMHZ_FILTER_CODE
        return params

    def fetch_new_calls(self) -> List[Call]:
        url = f"{self.base_url}/{self.system}/calls/newer"
        try:
            resp = httpx.get(url, params=self._params(), timeout=20.0)
            resp.raise_for_status()
            payload = resp.json()
        except (httpx.HTTPError, ValueError) as exc:
            print(f"[openmhz] fetch failed: {exc}", flush=True)
            return []

        raw_calls = payload.get("calls", []) if isinstance(payload, dict) else []
        calls: List[Call] = []
        max_cursor = self.cursor_ms
        for c in raw_calls:
            iso_ts = c.get("time", "")
            cursor = _iso_to_cursor_ms(iso_ts)
            if cursor is not None and cursor > max_cursor:
                max_cursor = cursor

            length = c.get("len")
            try:
                length = float(length) if length is not None else None
            except (TypeError, ValueError):
                length = None

            calls.append(
                Call(
                    external_id=str(c.get("_id")),
                    source=self.name,
                    audio_url=c.get("url"),
                    talkgroup=str(c.get("talkgroupNum")) if c.get("talkgroupNum") is not None else None,
                    timestamp=iso_ts or None,
                    length=length,
                    extra={"systemName": c.get("systemName"), "system": self.system},
                )
            )

        # Advance the cursor so we never re-fetch the same window.
        self.cursor_ms = max_cursor
        return calls
