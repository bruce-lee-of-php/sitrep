"""Manual injection helper — feed a transcript through the full pipeline.

Usage (inside the container or with DB env set):
    python inject.py "Units respond, protest forming at 5th and Main, ~200 people, urgent"
    python inject.py --file sample.txt

Runs transcribe(skipped for text) -> extract -> geocode -> store exactly as the
worker does, so you can verify a pin appears on the map without live audio.
"""
from __future__ import annotations

import argparse
import sys

import store
from extract.base import get_extractor
from pipeline import process_call
from sources.text_ingest import TextSource


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Inject a text transmission.")
    parser.add_argument("text", nargs="?", help="Transcript text to ingest.")
    parser.add_argument("--file", help="Read transcript from a file instead.")
    args = parser.parse_args(argv)

    if args.file:
        with open(args.file, "r", encoding="utf-8") as fh:
            text = fh.read().strip()
    elif args.text:
        text = args.text.strip()
    else:
        parser.error("provide transcript text or --file")
        return 2

    conn = store.get_connection()
    store.init_schema(conn)
    extractor = get_extractor()

    source = TextSource([text])
    for call in source.fetch_new_calls():
        process_call(conn, call, extractor)

    conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
