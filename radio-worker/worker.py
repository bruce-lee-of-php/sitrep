"""radio-worker entrypoint.

Polls the configured source on an interval and runs each new call through the
processing pipeline. Text is the active source; OpenMHz is scaffolded for later.
"""
from __future__ import annotations

import time

import config
import store
from extract.base import get_extractor
from pipeline import process_call
from sources.base import RadioSource


def build_source() -> RadioSource:
    if config.SOURCE == "text":
        from sources.text_ingest import FileInboxSource

        print(
            f"[worker] source=text inbox={config.TEXT_INBOX_DIR} "
            f"archive={config.TEXT_ARCHIVE_DIR}",
            flush=True,
        )
        return FileInboxSource(config.TEXT_INBOX_DIR, config.TEXT_ARCHIVE_DIR)

    if config.SOURCE == "mastodon":
        from sources.mastodon import MastodonSource

        print(
            f"[worker] source=mastodon instance={config.MASTODON_INSTANCE} "
            f"account={config.MASTODON_ACCOUNT}",
            flush=True,
        )
        return MastodonSource()

    if config.SOURCE == "rss":
        from sources.rss import RssSource

        print(f"[worker] source=rss feeds={len(config.RSS_FEEDS)}", flush=True)
        return RssSource()

    if config.SOURCE == "openmhz":
        from sources.openmhz import OpenMHzSource

        print(f"[worker] source=openmhz system={config.OPENMHZ_SYSTEM}", flush=True)
        return OpenMHzSource()

    raise ValueError(f"Unknown RADIO_SOURCE: {config.SOURCE!r}")


def wait_for_db():
    """Block until the database accepts a connection (db container may lag)."""
    while True:
        try:
            conn = store.get_connection()
            conn.close()
            return
        except Exception as exc:  # noqa: BLE001
            print(f"[worker] waiting for db: {exc}", flush=True)
            time.sleep(2)


def main():
    print("[worker] starting radio-worker", flush=True)
    wait_for_db()

    conn = store.get_connection()
    store.init_schema(conn)

    source = build_source()
    extractor = get_extractor()
    print(f"[worker] extractor={extractor.name} poll={config.POLL_INTERVAL}s", flush=True)

    while True:
        try:
            calls = source.fetch_new_calls()
            if calls:
                print(f"[worker] {len(calls)} new call(s)", flush=True)
            for call in calls:
                if call.length is not None and call.length < config.MIN_CALL_LENGTH:
                    continue
                try:
                    process_call(conn, call, extractor)
                except Exception as exc:  # noqa: BLE001 — one bad call shouldn't kill the loop
                    print(f"[worker] error processing {call.external_id}: {exc}", flush=True)
                    conn.rollback()
        except Exception as exc:  # noqa: BLE001
            print(f"[worker] poll error: {exc}", flush=True)
            # Reconnect on connection-level failures.
            try:
                conn.close()
            except Exception:  # noqa: BLE001
                pass
            wait_for_db()
            conn = store.get_connection()

        time.sleep(config.POLL_INTERVAL)


if __name__ == "__main__":
    main()
